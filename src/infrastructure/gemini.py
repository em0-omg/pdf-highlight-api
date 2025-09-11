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
        図面画像内の銃弾型記号を検出し、座標情報を取得する

        Args:
            image: PIL Imageオブジェクト
            target_texts: 検出対象のテキストリスト（デフォルト: PF100, PF150）

        Returns:
            dict: 検出結果と座標情報
        """
        target_list = ", ".join(target_texts)

        coordinate_prompt = f"""
この図面画像から以下の条件を満たす記号のみを検出してください。

**検出条件**：
1. 赤い枠で囲まれた図面部分内に存在すること
2. 銃弾型の形状をした記号（先端が丸く、後部が四角い）
3. その記号に線、矢印、引き出し線で「{target_list}」の文字が関連付けられている
4. 記号と文字が視覚的に明確に関連している（線で接続されている）

**重要な注意点**：
- 赤枠の外側にある文字は完全に無視する
- 赤枠内の図面部分のみを分析対象とする  
- 記号の形状が銃弾型（カプセル型、先丸後角）であることを厳密に確認
- 単なる円形や四角形の記号は対象外
- 文字だけで記号と関連付けられていないものは除外
- 記号と文字を結ぶ線や矢印が明確に見える場合のみ検出

**検出手順**：
1. まず赤い枠の位置を特定し、その内側のエリアのみを注目する
2. 赤枠内で銃弾型の記号を探す（先端が丸く後部が四角い形状）
3. その記号から線や矢印で文字に接続されているかを確認
4. 接続された文字が「PF100」または「PF150」であることを確認
5. 記号と文字の両方の座標を記録する

JSON形式で厳密に回答:
{{
    "detections": [
        {{
            "text": "関連する文字（PF100またはPF150）",
            "symbol_bbox": [記号のx座標, y座標, 幅, 高さ],
            "text_bbox": [文字のx座標, y座標, 幅, 高さ],
            "confidence": 0.0から1.0の信頼度,
            "symbol_shape": "bullet_like",
            "has_connection": true,
            "inside_red_frame": true
        }}
    ],
    "summary": {{
        "total_detections": 検出総数,
        "pf100_count": PF100関連記号の数,
        "pf150_count": PF150関連記号の数,
        "note": "赤枠内の銃弾型記号とPF100/PF150文字の関連付けを検出"
    }}
}}

必ずJSON形式で回答し、他の説明は一切含めないでください。
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
        target_list = ", ".join(target_texts)
        
        flexible_prompt = f"""
この画像を注意深く観察し、以下の条件に完全に合致するもののみを検出してください：

**厳格な検出条件**：
1. 赤い枠で囲まれた図面エリア内のみを検索対象とする
2. 銃弾型または楕円と四角の組み合わせの記号を探す
3. その記号から矢印、線、引き出し線で「{target_list}」という文字列に接続されている
4. 記号と文字の間に明確な視覚的関連性がある（線で結ばれている）

**除外すべきもの**：
- 赤枠の外側にある全ての文字・記号
- 記号と関連付けられていない単独の文字
- 銃弾型ではない単純な図形
- 線や矢印で接続されていない文字

**検出要件**：
- 記号は赤枠内に存在すること
- 記号の形状が明確に銃弾型またはカプセル型であること  
- 記号と文字が線・矢印・引き出し線で物理的に接続されていること
- 接続された文字がPF100またはPF150であること

以下の形式で回答してください：
{{
    "detections": [
        {{
            "text": "見つけた文字列",
            "symbol_bbox": [記号のx座標, y座標, 幅, 高さ],
            "text_bbox": [文字のx座標, y座標, 幅, 高さ],
            "confidence": 信頼度(0.1-1.0),
            "has_connection": true,
            "inside_red_frame": true
        }}
    ],
    "summary": {{
        "total_detections": 見つけた総数,
        "pf100_count": PF100の個数,
        "pf150_count": PF150の個数,
        "note": "赤枠内で記号と文字が線で接続されたもののみ"
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
        summary = {"total_detections": 0, "pf100_count": 0, "pf150_count": 0}
        
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
            
            if "pf100" in text.lower():
                summary["pf100_count"] = count
            elif "pf150" in text.lower():
                summary["pf150_count"] = count
                
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
        summary = {"total_detections": 0, "pf100_count": 0, "pf150_count": 0}

        for text in target_texts:
            count = response_text.upper().count(text.upper())
            if "pf100" in text.lower():
                summary["pf100_count"] = count
            elif "pf150" in text.lower():
                summary["pf150_count"] = count
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

                # テキストのハイライト（symbol_bboxがない場合のフォールバック）
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
                            width=2,
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
