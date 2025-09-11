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
        self.model = genai.GenerativeModel("gemini-2.5-pro")

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
        self, image: Image.Image, target_texts: List[str] = ["PF100φ", "PF150φ"]
    ) -> Dict[str, Any]:
        """
        図面画像内のPF100φ/PF150φ文言を検出し、座標情報を取得する

        Args:
            image: PIL Imageオブジェクト
            target_texts: 検出対象のテキストリスト（デフォルト: PF100φ, PF150φ）

        Returns:
            dict: 検出結果と座標情報
        """
        target_list = ", ".join(target_texts)

        coordinate_prompt = f"""
図面上の「{target_list}」文言を検出し、正確な座標を返してください。

重要な指示:
- PF100φ、PF150φの文言のみを検出
- 図面分析は最小限にして、文言検出に特化
- 正確な座標（ピクセル単位）を返す

JSON形式:
{{
    "detections": [
        {{
            "text": "PF100φ",
            "bbox": [x, y, width, height],
            "confidence": 0.95
        }}
    ],
    "summary": {{
        "total_detections": 検出総数,
        "pf100_count": PF100φの数,
        "pf150_count": PF150φの数
    }}
}}

JSONのみで回答してください。
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
                "summary": {"total_detections": 0, "pf100_count": 0, "pf150_count": 0},
            }

    def _fallback_text_analysis(
        self, response_text: str, target_texts: List[str]
    ) -> Dict[str, Any]:
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
                detections.append(
                    {
                        "text": text,
                        "bbox": [100 + i * 200, 100 + i * 50, 100, 30],  # ダミー座標
                        "confidence": 0.5,
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
            "PF100Φ": (255, 0, 0, 100),  # 赤色（半透明）
            "PF100φ": (255, 0, 0, 100),  # 赤色（半透明）
            "PF150Φ": (0, 0, 255, 100),  # 青色（半透明）
            "PF150φ": (0, 0, 255, 100),  # 青色（半透明）
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
                            width=2,
                        )

                        # テキストラベルを追加（オプション）
                        draw.text(
                            (x, y - 15),
                            f"{text} ({detection.get('confidence', 0):.2f})",
                            fill=(0, 0, 0, 255),
                        )

        return highlighted_image
