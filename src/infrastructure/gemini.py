import os
import json
from typing import List, Dict, Any
import google.generativeai as genai
from PIL import Image, ImageDraw


class GeminiImageAnalyzer:
    """
    Gemini APIを使用した画像分析クラス
    """

    def __init__(self, model_name: str = "gemini-2.5-pro"):
        """
        GeminiImageAnalyzerの初期化
        環境変数GEMINI_API_KEYからAPIキーを取得
        
        Args:
            model_name: 使用するGeminiモデル名（デフォルト: gemini-2.5-pro）
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name

    async def analyze_image(
        self,
        image: Image.Image,
        prompt: str = "この画像の内容を詳しく説明してください。",
    ) -> str:
        """
        画像を分析する

        Args:
            image: PIL Imageオブジェクト
            prompt: 分析用プロンプト

        Returns:
            str: Geminiからの分析結果
        """
        try:
            response = self.model.generate_content([prompt, image])
            return response.text
        except Exception as e:
            raise Exception(f"画像分析エラー: {str(e)}")

    async def analyze_images(
        self,
        images: List[Image.Image],
        prompt: str = "この画像の内容を詳しく説明してください。",
    ) -> List[str]:
        """
        複数画像を分析する

        Args:
            images: PIL Imageオブジェクトのリスト
            prompt: 分析用プロンプト

        Returns:
            List[str]: 各画像の分析結果のリスト
        """
        results = []
        for i, image in enumerate(images):
            try:
                page_prompt = f"{prompt} (ページ {i+1})"
                result = await self.analyze_image(image, page_prompt)
                results.append(result)
            except Exception as e:
                results.append(f"ページ {i+1} の分析エラー: {str(e)}")

        return results

    async def analyze_image_with_coordinates(
        self, image: Image.Image, target_texts: List[str] = ["PF100", "PF150"]
    ) -> Dict[str, Any]:
        """
        図面画像内で指定されたキーワードを含む文字列を検出し、座標情報を取得する

        Args:
            image: PIL Imageオブジェクト
            target_texts: 検出対象のキーワードリスト（デフォルト: PF100, PF150）

        Returns:
            dict: 検出結果と座標情報
        """
        keywords_list = "、".join([f'「{text}」' for text in target_texts])
        
        coordinate_prompt = f"""
画像の赤い枠の中が図面です。
図面の中から{keywords_list}を含む文字列を全て検出してハイライトしてください。
記号や単位が付いた文字列、様々な表記のバリエーションも検出対象とします。

JSON形式で回答:
{{
    "detections": [
        {{
            "text": "検出された文字列",
            "text_bbox": [x座標, y座標, 幅, 高さ],
            "confidence": 0.8
        }}
    ],
    "summary": {{
        "total_detections": 検出総数
    }}
}}
"""

        try:
            response = self.model.generate_content([coordinate_prompt, image])
            response_text = response.text.strip()

            # JSONレスポンスのクリーニング
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()

            try:
                detection_data = json.loads(response_text)
                # 検出結果が空の場合は、より柔軟なプロンプトでリトライ
                if not detection_data.get("detections") or detection_data.get("summary", {}).get("total_detections", 0) == 0:
                    return await self._retry_with_flexible_prompt(image, target_texts)
                return detection_data
            except json.JSONDecodeError:
                # JSONパースに失敗した場合、より柔軟なプロンプトでリトライ
                return await self._retry_with_flexible_prompt(image, target_texts)

        except Exception as e:
            return {
                "error": f"座標検出エラー: {str(e)}",
                "detections": [],
                "summary": {"total_detections": 0, "pf100_count": 0, "pf150_count": 0},
            }

    async def _retry_with_flexible_prompt(
        self, image: Image.Image, target_texts: List[str]
    ) -> Dict[str, Any]:
        """
        より柔軟なプロンプトでのリトライ検出
        """
        flexible_keywords = "、".join([f'「{text}」' for text in target_texts])
        
        flexible_prompt = f"""
赤い枠の中の図面から{flexible_keywords}を含む文字列を全て見つけてください。
記号や単位が付いた文字列も含めて検出してください。

{{
    "detections": [
        {{
            "text": "見つけた文字列",
            "text_bbox": [x, y, 幅, 高さ],
            "confidence": 0.7
        }}
    ],
    "summary": {{
        "total_detections": 合計数
    }}
}}
"""
        
        try:
            response = self.model.generate_content([flexible_prompt, image])
            response_text = response.text.strip()
            
            # JSONレスポンスのクリーニング
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
                
            try:
                detection_data = json.loads(response_text)
                return detection_data
            except json.JSONDecodeError:
                # 最後の手段として改良されたフォールバック分析
                return self._enhanced_fallback_analysis(response_text, target_texts, image)
                
        except Exception as e:
            return self._enhanced_fallback_analysis(f"エラー: {str(e)}", target_texts, image)

    def _enhanced_fallback_analysis(
        self, response_text: str, target_texts: List[str], image: Image.Image
    ) -> Dict[str, Any]:
        """
        改良されたフォールバック分析 - 推測ベースでの検出
        """
        detections = []
        summary = {"total_detections": 0}
        
        # 画像サイズ情報を取得
        width, height = image.size
        
        # レスポンステキストから数値情報を推測
        import re
        
        for text in target_texts:
            # テキスト内でのキーワード出現回数をカウント（大文字小文字を無視）
            pattern = re.compile(re.escape(text.replace('φ', '[φΦ]')), re.IGNORECASE)
            matches = pattern.findall(response_text)
            count = len(matches)
            
            # より柔軟なパターンマッチング
            if count == 0:
                # PF100, PF150 などの数字部分でも検索
                number_pattern = re.search(r'PF(\d+)', text, re.IGNORECASE)
                if number_pattern:
                    number = number_pattern.group(1)
                    flexible_pattern = f"PF{number}"
                    flexible_matches = re.findall(flexible_pattern, response_text, re.IGNORECASE)
                    count = len(flexible_matches)
            
            # キーワードごとのカウントを記録（動的）
            keyword_key = f"{text.lower().replace('φ', 'phi').replace('Φ', 'phi')}_count"
            summary[keyword_key] = count
            summary["total_detections"] += count

            # 画像サイズに基づいた推測座標を生成
            for i in range(count):
                # 画像を格子状に分割して配置
                cols = max(1, int((count ** 0.5)))
                rows = max(1, (count + cols - 1) // cols)
                
                col = i % cols
                row = i // cols
                
                x = int(width * (col + 0.5) / cols - 50)  # 中心から50px左
                y = int(height * (row + 0.5) / rows - 15)  # 中心から15px上
                
                # 座標を有効な範囲に制限
                x = max(0, min(x, width - 100))
                y = max(0, min(y, height - 30))
                
                detections.append(
                    {
                        "text": text,
                        "bbox": [x, y, 100, 30],
                        "confidence": 0.3,  # フォールバック検出は信頼度を低く設定
                        "fallback": True
                    }
                )

        return {
            "detections": detections, 
            "summary": summary, 
            "fallback": True,
            "note": "推測ベースの検出結果"
        }

    def _fallback_text_analysis(
        self, response_text: str, target_texts: List[str]
    ) -> Dict[str, Any]:
        """
        JSON解析に失敗した場合の従来のフォールバック分析（後方互換性のため維持）
        """
        detections = []
        summary = {"total_detections": 0}

        for text in target_texts:
            count = response_text.upper().count(text.upper())
            # キーワードごとのカウントを記録（動的）
            keyword_key = f"{text.lower().replace('φ', 'phi').replace('Φ', 'phi')}_count"
            summary[keyword_key] = count
            summary["total_detections"] += count

            # ダミー座標
            for i in range(count):
                detections.append(
                    {
                        "text": text,
                        "bbox": [100 + i * 200, 100 + i * 50, 100, 30],
                        "confidence": 0.5,
                        "fallback": True
                    }
                )

        return {"detections": detections, "summary": summary, "fallback": True}

    def create_highlighted_image(
        self, original_image: Image.Image, detection_data: Dict[str, Any]
    ) -> Image.Image:
        """
        検出された座標にハイライトを追加した画像を生成

        Args:
            original_image: 元の画像
            detection_data: 座標検出結果

        Returns:
            Image.Image: ハイライト済み画像
        """
        # 画像をコピー（元画像を保持）
        highlighted_image = original_image.copy()
        draw = ImageDraw.Draw(highlighted_image)

        # 色設定
        color_map = {
            "PF100": (255, 0, 0, 120),    # 赤色（半透明）
            "PF100Φ": (255, 0, 0, 120),  # 赤色（半透明）
            "PF100φ": (255, 0, 0, 120),  # 赤色（半透明）
            "PF150": (0, 0, 255, 120),    # 青色（半透明）
            "PF150Φ": (0, 0, 255, 120),  # 青色（半透明）
            "PF150φ": (0, 0, 255, 120),  # 青色（半透明）
        }

        default_color = (0, 255, 0, 120)  # 緑色（その他のテキスト用）
        symbol_color = (255, 165, 0, 120)  # オレンジ色（記号用）

        if "detections" in detection_data:
            for detection in detection_data["detections"]:
                text = detection.get("text", "")
                
                # 銃弾型記号のハイライト（優先）
                symbol_bbox = detection.get("symbol_bbox", [])
                if symbol_bbox and len(symbol_bbox) >= 4:
                    x, y, width, height = symbol_bbox
                    
                    # 座標の有効性チェック
                    if all(coord >= 0 for coord in symbol_bbox) and width > 0 and height > 0:
                        # 銃弾型記号を太い枠で囲む
                        draw.rectangle(
                            [x, y, x + width, y + height],
                            fill=symbol_color,
                            outline=(255, 140, 0, 255),  # 濃いオレンジの枠線
                            width=4,
                        )
                        
                        # 記号の中央にラベルを追加
                        center_x = x + width // 2
                        center_y = y + height // 2
                        draw.text(
                            (center_x - 20, center_y - 10),
                            "記号",
                            fill=(255, 255, 255, 255),
                            stroke_width=1,
                            stroke_fill=(0, 0, 0, 255)
                        )

                # テキストのハイライト
                text_bbox = detection.get("text_bbox", detection.get("bbox", []))
                if text_bbox and len(text_bbox) >= 4:
                    x, y, width, height = text_bbox

                    # 座標の有効性チェック
                    if all(coord >= 0 for coord in text_bbox) and width > 0 and height > 0:
                        # ハイライト色を選択
                        color = color_map.get(text.upper(), default_color)

                        # 矩形ハイライトを描画
                        draw.rectangle(
                            [x, y, x + width, y + height],
                            fill=color,
                            outline=(color[0], color[1], color[2], 255),  # 枠線は不透明
                            width=3,
                        )

                        # テキストラベルを追加
                        draw.text(
                            (x, y - 20),
                            f"{text}",
                            fill=(0, 0, 0, 255),
                            stroke_width=1,
                            stroke_fill=(255, 255, 255, 255)
                        )

                # 古い形式のbboxにも対応（後方互換性）
                elif not symbol_bbox and not text_bbox:
                    bbox = detection.get("bbox", [])
                    if bbox and len(bbox) >= 4:
                        x, y, width, height = bbox

                        # 座標の有効性チェック
                        if all(coord >= 0 for coord in bbox) and width > 0 and height > 0:
                            # ハイライト色を選択
                            color = color_map.get(text.upper(), default_color)

                            # 矩形ハイライトを描画
                            draw.rectangle(
                                [x, y, x + width, y + height],
                                fill=color,
                                outline=(color[0], color[1], color[2], 255),  # 枠線は不透明
                                width=3,
                            )

                            # テキストラベルを追加
                            draw.text(
                                (x, y - 15),
                                f"{text} ({detection.get('confidence', 0):.2f})",
                                fill=(0, 0, 0, 255),
                            )

        return highlighted_image
