import os
import json
from typing import List, Dict, Any
import google.generativeai as genai
from PIL import Image, ImageDraw


class GeminiImageAnalyzer:
    """
    Gemini APIを使用した画像分析クラス
    """
    
    def __init__(self):
        """
        GeminiImageAnalyzerの初期化
        環境変数GEMINI_API_KEYからAPIキーを取得
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
    
    async def analyze_image(self, image: Image.Image, prompt: str = "この画像の内容を詳しく説明してください。") -> str:
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
    
    async def analyze_images(self, images: List[Image.Image], prompt: str = "この画像の内容を詳しく説明してください。") -> List[str]:
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
    
    async def analyze_pdf_content(self, images: List[Image.Image], analysis_type: str = "general") -> dict:
        """
        PDFから変換された画像を総合的に分析する
        
        Args:
            images: PDFから変換された画像のリスト
            analysis_type: 分析タイプ ("general", "summary", "extract_text", "highlight_points")
            
        Returns:
            dict: 分析結果と詳細情報
        """
        prompts = {
            "general": "この文書の内容を詳しく説明してください。",
            "summary": "この文書の要約を作成してください。",
            "extract_text": "この文書のテキスト内容を抽出してください。",
            "highlight_points": "この文書の重要なポイントを箇条書きで説明してください。"
        }
        
        prompt = prompts.get(analysis_type, prompts["general"])
        
        try:
            # 全体分析
            if len(images) > 1:
                # 複数ページの場合は全体分析
                all_images_content = [prompt + " (全体分析)"] + images
                overall_response = self.model.generate_content(all_images_content)
                overall_analysis = overall_response.text
                
                # 各ページの個別分析
                page_analyses = await self.analyze_images(images, f"{prompt} (個別分析)")
                
                return {
                    "overall_analysis": overall_analysis,
                    "page_analyses": page_analyses,
                    "total_pages": len(images),
                    "analysis_type": analysis_type
                }
            else:
                # 単一ページの場合
                single_analysis = await self.analyze_image(images[0], prompt)
                return {
                    "overall_analysis": single_analysis,
                    "page_analyses": [single_analysis],
                    "total_pages": 1,
                    "analysis_type": analysis_type
                }
                
        except Exception as e:
            return {
                "error": f"PDF分析エラー: {str(e)}",
                "total_pages": len(images),
                "analysis_type": analysis_type
            }
    
    async def analyze_image_with_coordinates(self, image: Image.Image, target_texts: List[str] = ["PF100", "PF150"]) -> Dict[str, Any]:
        """
        画像内の特定テキストを検出し、座標情報を取得する
        
        Args:
            image: PIL Imageオブジェクト
            target_texts: 検出対象のテキストリスト
            
        Returns:
            dict: 検出結果と座標情報
        """
        target_list = ", ".join(target_texts)
        
        coordinate_prompt = f"""
この画像内で「{target_list}」の文字列を全て検出し、以下のJSON形式で座標情報を返してください。
画像の左上を(0,0)として、各テキストの位置を正確に特定してください。

必須返答形式（JSON）:
{{
    "detections": [
        {{
            "text": "検出されたテキスト",
            "bbox": [x, y, width, height],
            "confidence": 0.95
        }}
    ],
    "summary": {{
        "total_detections": 検出総数,
        "pf100_count": PF100の検出数,
        "pf150_count": PF150の検出数
    }}
}}

重要な注意点:
- 座標は画像のピクセル単位で指定してください
- 複数の同じテキストが検出された場合は、全て含めてください
- テキストが不明瞭でも、可能性のある箇所は含めてください
- 必ずJSON形式のみで回答してください
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
                return detection_data
            except json.JSONDecodeError:
                # JSONパースに失敗した場合、テキスト分析にフォールバック
                return self._fallback_text_analysis(response_text, target_texts)
                
        except Exception as e:
            return {
                "error": f"座標検出エラー: {str(e)}",
                "detections": [],
                "summary": {"total_detections": 0, "pf100_count": 0, "pf150_count": 0}
            }
    
    def _fallback_text_analysis(self, response_text: str, target_texts: List[str]) -> Dict[str, Any]:
        """
        JSON解析に失敗した場合のフォールバック分析
        """
        detections = []
        summary = {"total_detections": 0, "pf100_count": 0, "pf150_count": 0}
        
        for text in target_texts:
            count = response_text.upper().count(text.upper())
            summary[f"{text.lower()}_count"] = count
            summary["total_detections"] += count
            
            # ダミー座標（実際の実装では画像分析結果から推定）
            for i in range(count):
                detections.append({
                    "text": text,
                    "bbox": [100 + i * 200, 100 + i * 50, 100, 30],  # ダミー座標
                    "confidence": 0.5
                })
        
        return {
            "detections": detections,
            "summary": summary,
            "fallback": True
        }
    
    def create_highlighted_image(self, original_image: Image.Image, detection_data: Dict[str, Any]) -> Image.Image:
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
            "PF100": (255, 0, 0, 100),    # 赤色（半透明）
            "PF150": (0, 0, 255, 100),    # 青色（半透明）
        }
        
        default_color = (0, 255, 0, 100)  # 緑色（その他のテキスト用）
        
        if "detections" in detection_data:
            for detection in detection_data["detections"]:
                text = detection.get("text", "")
                bbox = detection.get("bbox", [0, 0, 0, 0])
                
                if len(bbox) >= 4:
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
                            width=2
                        )
                        
                        # テキストラベルを追加（オプション）
                        draw.text(
                            (x, y - 15),
                            f"{text} ({detection.get('confidence', 0):.2f})",
                            fill=(0, 0, 0, 255)
                        )
        
        return highlighted_image