import os
import json
import logging
from typing import List, Dict, Any, Optional
import google.genai as genai
from google.genai import types
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

        # New google.genai client
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    # ---- Payload builders (google.genai) -------------------------------
    def _pil_to_part(self, image: Image.Image, mime_type: str = "image/png") -> types.Part:
        import io

        buf = io.BytesIO()
        # Use PNG to avoid JPEG artifacts for diagrams
        fmt = "PNG" if mime_type == "image/png" else "JPEG"
        image.save(buf, format=fmt)
        return types.Part.from_bytes(data=buf.getvalue(), mime_type=mime_type)

    def _build_contents(self, prompt: str, *images: Image.Image) -> List[types.Content]:
        parts: List[types.Part] = [types.Part.from_text(text=prompt)]
        for img in images:
            parts.append(self._pil_to_part(img))
        return [types.Content(role="user", parts=parts)]

    # ---- Internal helpers -------------------------------------------------
    def _extract_structured(self, response) -> Optional[Dict[str, Any]]:
        """Extract structured JSON from Gemini response with multiple fallbacks.

        Order:
        1) response.parsed (SDK structured output)
        2) response.candidates[].content.parts[].inline_data (application/json)
        3) response.text (parse as JSON)
        Returns dict or None.
        """
        try:
            # 1) Preferred structured output
            parsed = getattr(response, "parsed", None)
            if parsed is not None:
                try:
                    # pydantic model or plain dict
                    if hasattr(parsed, "model_dump"):
                        return parsed.model_dump()
                    if isinstance(parsed, (dict, list)):
                        return parsed  # type: ignore[return-value]
                except Exception:
                    pass

            # 2) Inline JSON in parts
            candidates = getattr(response, "candidates", None) or []
            for c in candidates:
                content = getattr(c, "content", None)
                parts = getattr(content, "parts", None) or []
                for p in parts:
                    inline = getattr(p, "inline_data", None)
                    if inline is not None:
                        mime = getattr(inline, "mime_type", "") or ""
                        data = getattr(inline, "data", b"")
                        if "json" in mime:
                            try:
                                if isinstance(data, (bytes, bytearray)):
                                    return json.loads(data.decode("utf-8"))
                                if isinstance(data, str):
                                    return json.loads(data)
                            except Exception:
                                pass

            # 3) Fallback to text JSON
            text = getattr(response, "text", None)
            if isinstance(text, str) and text.strip():
                try:
                    return json.loads(text)
                except Exception:
                    return None
        except Exception:
            return None

        return None

    # ---- BBox helpers -------------------------------------------------------
    def _to_pixel_bbox(self, raw_bbox: Any, img_w: int, img_h: int):
        """Coerce various bbox formats to pixel [x, y, w, h].

        Accepts:
        - dict: {x,y,w,h} or {x1,y1,x2,y2} or {box_2d:[ymin,xmin,ymax,xmax]}
        - list/tuple: [x,y,w,h] or [x1,y1,x2,y2]
        All coordinates are expected to be in [0,1000] normalized format.
        Returns tuple (x,y,w,h) in pixels or None.
        """
        if not raw_bbox:
            return None

        def clip_and_pack(x, y, w, h):
            x, y, w, h = int(round(x)), int(round(y)), int(round(w)), int(round(h))
            if w <= 0 or h <= 0:
                return None
            x = max(0, min(x, img_w - 1))
            y = max(0, min(y, img_h - 1))
            w = max(1, min(w, img_w - x))
            h = max(1, min(h, img_h - y))
            return x, y, w, h

        if isinstance(raw_bbox, dict):
            if "box_2d" in raw_bbox and isinstance(raw_bbox["box_2d"], (list, tuple)) and len(raw_bbox["box_2d"]) >= 4:
                ymin, xmin, ymax, xmax = raw_bbox["box_2d"][:4]
                # Always expect [0,1000] normalized coordinates
                sx, sy = img_w / 1000.0, img_h / 1000.0
                x1, y1 = xmin * sx, ymin * sy
                x2, y2 = xmax * sx, ymax * sy
                return clip_and_pack(x1, y1, x2 - x1, y2 - y1)

            if all(k in raw_bbox for k in ("x", "y", "w", "h")):
                x, y, w, h = raw_bbox["x"], raw_bbox["y"], raw_bbox["w"], raw_bbox["h"]
                # Convert from [0,1000] to pixels
                x, y, w, h = x * img_w / 1000, y * img_h / 1000, w * img_w / 1000, h * img_h / 1000
                return clip_and_pack(x, y, w, h)

            if all(k in raw_bbox for k in ("x1", "y1", "x2", "y2")):
                x1, y1, x2, y2 = raw_bbox["x1"], raw_bbox["y1"], raw_bbox["x2"], raw_bbox["y2"]
                # Convert from [0,1000] to pixels
                x1, y1, x2, y2 = x1 * img_w / 1000, y1 * img_h / 1000, x2 * img_w / 1000, y2 * img_h / 1000
                return clip_and_pack(x1, y1, x2 - x1, y2 - y1)

            return None

        if isinstance(raw_bbox, (list, tuple)) and len(raw_bbox) >= 4:
            a, b, c, d = raw_bbox[:4]
            # Always expect [0,1000] normalized
            a, b, c, d = a * img_w / 1000, b * img_h / 1000, c * img_w / 1000, d * img_h / 1000

            # Heuristic: treat as [x1,y1,x2,y2] if c>a and d>b
            if c > a and d > b:
                return clip_and_pack(a, b, c - a, d - b)
            # Otherwise [x,y,w,h]
            return clip_and_pack(a, b, c, d)

        return None

    async def describe_target_image(
        self, custom_target_image: Image.Image = None
    ) -> Dict[str, Any]:
        """
        ターゲット画像の特徴をGeminiに説明させ、読み込み確認用の情報を返す

        Args:
            custom_target_image: カスタムターゲット画像（未指定の場合はデフォルトのtarget.png）

        Returns:
            dict: 説明結果と画像メタ情報
        """
        import pathlib

        # ターゲット画像の決定（カスタム優先、なければデフォルト）
        source = "custom" if custom_target_image is not None else "default"
        if custom_target_image is not None:
            target_image = custom_target_image
        else:
            target_image_path = (
                pathlib.Path(__file__).parent.parent
                / "assets"
                / "images"
                / "target.png"
            )
            if not target_image_path.exists():
                raise FileNotFoundError(f"Target image not found: {target_image_path}")
            target_image = Image.open(target_image_path)

        width, height = target_image.size

        prompt = (
            "次のターゲット画像の視覚的な特徴を日本語で短く説明してください。"
            "形状、模様、線やマーク、色（白黒ならその旨）、相対的な比率など、"
            "識別に有用なポイントを箇条書き風に3〜6点でまとめてください。"
        )

        try:
            description = await self.analyze_image(target_image, prompt)
        except Exception as e:
            description = f"説明取得に失敗: {str(e)}"

        return {
            "source": source,
            "width": width,
            "height": height,
            "model": self.model_name,
            "description": description,
        }

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
            contents = self._build_contents(prompt, image)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
            )
            return response.text
        except Exception as e:
            raise Exception(f"画像分析エラー: {str(e)}")

    async def analyze_pdf_document(
        self,
        pdf_bytes: bytes,
        prompt: Optional[str] = None,
        *,
        debug: bool = False,
    ) -> Dict[str, Any]:
        """
        PDFドキュメントをGeminiに直接渡し、構造化JSONで結果を取得する。

        - 対象: 建築図面PDF
        - 目的: PF100 または FD付の PF150 を検出し、可能なら座標(x,y)とbboxを返す

        Args:
            pdf_bytes: PDFファイルの生バイト列
            prompt: 追加/上書き用の指示文（省略時は推奨プロンプトを使用）
            debug: デバッグ情報を付与する

        Returns:
            Dict[str, Any]: 構造化された検出結果
        """
        # 出力スキーマ（Structured Output）
        detection_schema: Dict[str, Any] = {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "object",
                    "properties": {
                        "total_detections": {"type": "integer"},
                        "pf100_count": {"type": "integer"},
                        "pf150_fd_count": {"type": "integer"},
                        "notes": {"type": "string"},
                    },
                    "required": ["total_detections", "pf100_count", "pf150_fd_count"],
                },
                "pages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "page": {"type": "integer"},
                            "detections": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "target": {
                                            "type": "string",
                                            "enum": ["PF100", "PF150_FD"],
                                        },
                                        "position": {
                                            "type": "object",
                                            "properties": {
                                                "x": {"type": "integer", "minimum": 0, "maximum": 1000},
                                                "y": {"type": "integer", "minimum": 0, "maximum": 1000},
                                            },
                                            "required": ["x", "y"],
                                        },
                                        "bbox": {
                                            "type": "array",
                                            "items": {"type": "integer", "minimum": 0, "maximum": 1000},
                                            "minItems": 4,
                                            "maxItems": 4,
                                            "description": "[x, y, width, height] normalized to [0,1000]",
                                        },
                                        "confidence": {"type": "number"},
                                        "rationale": {"type": "string"},
                                    },
                                    "required": ["target", "position"],
                                },
                            },
                        },
                        "required": ["page", "detections"],
                    },
                },
            },
            "required": ["summary", "pages"],
        }

        base_prompt = (
            "あなたは図面解析の専門アシスタントです。"
            "次のPDFは建築図面です。各ページごとに以下を厳密に検出してください:\n"
            "- 100mm径パイプシャフト（PF100）\n"
            "- 防火ダンパー付き（FD付）の150mm径パイプシャフト（PF150）\n\n"
            "出力要件:\n"
            "- スキーマに沿ったJSONのみを返すこと（追加の説明文は返さない）\n"
            "- 検出対象以外は含めない\n"
            "- 座標は[0,1000]の範囲に正規化して返すこと。ページの左上を(0,0)、右下を(1000,1000)とする\n"
            "- position.x, position.y は[0,1000]の整数で記録\n"
            "- 矩形が分かる場合は bbox=[x,y,width,height] を[0,1000]の範囲で併記\n"
            "- ページごとの件数と全体の件数をsummaryに集計\n"
            "- 検出がなければ該当ページのdetectionsは空配列\n"
            "- PF150( FD付 )は target='PF150_FD' として統一\n"
        )

        final_prompt = base_prompt if not prompt else (base_prompt + "\n補足指示:\n" + prompt)

        try:
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=final_prompt),
                        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    ],
                )
            ]

            generation_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=detection_schema,
            )

            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=generation_config,
                )
            except Exception:
                # 一部環境でstructured output未対応な場合のフォールバック
                fallback_prompt = (
                    final_prompt
                    + "\n\n必ず次の形式のJSONのみを返してください: "
                    + json.dumps(
                        {
                            "summary": {
                                "total_detections": 0,
                                "pf100_count": 0,
                                "pf150_fd_count": 0,
                            },
                            "pages": [],
                        }
                    )
                )
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_text(text=fallback_prompt),
                                types.Part.from_bytes(
                                    data=pdf_bytes, mime_type="application/pdf"
                                ),
                            ],
                        )
                    ],
                )

            data = self._extract_structured(response)
            response_text = (getattr(response, "text", None) or "").strip()

            if not isinstance(data, dict) or not data:
                # テキストからのフォールバックJSONパース
                try:
                    data = json.loads(response_text) if response_text else None
                except Exception:
                    data = None

            if not isinstance(data, dict) or "summary" not in data or "pages" not in data:
                fb: Dict[str, Any] = {
                    "summary": {
                        "total_detections": 0,
                        "pf100_count": 0,
                        "pf150_fd_count": 0,
                        "notes": "fallback: failed to parse structured output",
                    },
                    "pages": [],
                }
                if debug:
                    fb["_debug"] = {
                        "prompt": final_prompt,
                        "raw_response_text": response_text,
                        "model": self.model_name,
                    }
                return fb

            if debug:
                data.setdefault("_debug", {})
                try:
                    data["_debug"].update(
                        {
                            "prompt": final_prompt,
                            "raw_response_text": response_text or json.dumps(data),
                            "model": self.model_name,
                        }
                    )
                except Exception:
                    pass

            return data
        except Exception as e:
            raise Exception(f"PDF分析エラー: {str(e)}")

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

    async def analyze_symbol_with_coordinates(
        self,
        image: Image.Image,
        custom_target_image: Image.Image = None,
        *,
        debug: bool = False,
        target_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        図面画像内で指定された記号画像と同じ形状の記号を検出し、座標情報を取得する

        Args:
            image: PIL Imageオブジェクト
            custom_target_image: カスタムターゲット画像（オプション）

        Returns:
            dict: 検出結果と座標情報
        """
        # ターゲット画像の準備
        if custom_target_image:
            target_image = custom_target_image
        else:
            # デフォルトのtarget.png画像を読み込む
            import pathlib

            target_image_path = (
                pathlib.Path(__file__).parent.parent
                / "assets"
                / "images"
                / "target.png"
            )

            if not target_image_path.exists():
                raise FileNotFoundError(f"Target image not found: {target_image_path}")

            target_image = Image.open(target_image_path)

        # 画像サイズを取得
        img_w, img_h = image.size

        # ターゲット説明（任意）
        target_note = (
            f"\n参考となるターゲットの特徴:\n{target_description}\n"
            if target_description
            else ""
        )

        coordinate_prompt = (
            "あなたは図面上の記号検出器です。"
            "赤枠があれば枠内のみを解析し、参照画像（target.png）と同一形状の記号のみ検出。"
            "回転・スケール差やノイズに頑健に一致させ、誤検出は避ける。"
            "座標は必ず[0,1000]の範囲に正規化して返すこと。"
            "画像の左上を(0,0)、右下を(1000,1000)とする正規化座標系を使用。"
            "各検出は 'symbol_bbox': [x, y, width, height] を[0,1000]の範囲で返してください。"
            "補助として 'box_2d': [ymin, xmin, ymax, xmax] も[0,1000]の範囲で含めてもよい。"
            "値は必ず0以上1000以下の整数で返すこと。"
            f"{target_note}"
        )

        detection_schema: Dict[str, Any] = {
            "type": "object",
            "properties": {
                "image_size": {
                    "type": "object",
                    "properties": {
                        "width": {"type": "integer"},
                        "height": {"type": "integer"},
                        "unit": {"type": "string", "enum": ["px"]},
                    },
                    "required": ["width", "height", "unit"],
                },
                "coordinate_space": {"type": "string", "enum": ["pixel"]},
                "detections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "symbol_type": {"type": "string"},
                            "symbol_bbox": {
                                "type": "array",
                                "items": {"type": "number", "minimum": 0, "maximum": 1000},
                                "minItems": 4,
                                "maxItems": 4,
                                "description": "[x, y, width, height] normalized to [0,1000]"
                            },
                            "box_2d": {
                                "type": "array",
                                "items": {"type": "number", "minimum": 0, "maximum": 1000},
                                "minItems": 4,
                                "maxItems": 4,
                                "description": "[ymin, xmin, ymax, xmax] normalized to [0,1000]"
                            },
                            "confidence": {"type": "number"},
                            "rationale": {"type": "string"},
                            "matched_features": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["confidence"],
                    },
                },
                "summary": {
                    "type": "object",
                    "properties": {
                        "total_detections": {"type": "integer"},
                        "notes": {"type": "string"},
                    },
                    "required": ["total_detections"],
                },
            },
            "required": ["detections", "summary"],
        }

        try:
            # 構造化出力を有効化
            generation_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=detection_schema,
            )
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=self._build_contents(coordinate_prompt, image, target_image),
                    config=generation_config,
                )
            except Exception as e:
                # 一部SDK/モデルでstructured outputが未対応な場合のフォールバック
                fallback_prompt = (
                    coordinate_prompt
                    + "必ず次の形式のJSONのみを返してください: "
                    + json.dumps(
                        {
                            "detections": [
                                {"symbol_bbox": [0, 0, 0, 0], "confidence": 0.0}
                            ],
                            "summary": {"total_detections": 0},
                        }
                    )
                )
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=self._build_contents(fallback_prompt, image, target_image),
                )
            # Structured output: prefer response.parsed (SDK >=0.7)
            detection_data = None
            detection_data = self._extract_structured(response)
            response_text = (getattr(response, "text", None) or "").strip()

            try:
                if detection_data is None:
                    # JSONパースに失敗した場合のフォールバック
                    fb = {
                        "error": "JSON解析エラー",
                        "detections": [],
                        "summary": {"total_detections": 0},
                    }
                    if debug:
                        fb["_debug"] = {
                            "prompt": coordinate_prompt,
                            "raw_response_text": response_text,
                            "model": self.model_name,
                        }
                    return fb

                # Ensure coordinate_space is set
                detection_data["coordinate_space"] = "normalized_1000"
                
                if debug:
                    detection_data.setdefault("_debug", {})
                    detection_data["_debug"].update(
                        {
                            "prompt": coordinate_prompt,
                            "raw_response_text": response_text or json.dumps(detection_data),
                            "model": self.model_name,
                            "coordinate_space": "normalized_1000",
                        }
                    )
                    # 返却オブジェクトはJSONシリアライズ可能なプリミティブに限定する
                    try:
                        cands = getattr(response, "candidates", None)
                        detection_data["_debug"]["candidates_count"] = (
                            (len(cands) if hasattr(cands, "__len__") else None)
                        )
                        pf = getattr(response, "prompt_feedback", None)
                        detection_data["_debug"]["prompt_feedback"] = (
                            str(pf) if pf is not None else None
                        )
                    except Exception:
                        pass
                return detection_data
            except json.JSONDecodeError:
                # ここには通常来ないが互換のため保持
                fb = {
                    "error": "JSON解析エラー",
                    "detections": [],
                    "summary": {"total_detections": 0},
                }
                if debug:
                    fb["_debug"] = {
                        "prompt": coordinate_prompt,
                        "raw_response_text": (getattr(response, "text", None) or ""),
                        "model": self.model_name,
                    }
                return fb

        except Exception as e:
            fb = {
                "error": f"座標検出エラー: {str(e)}",
                "detections": [],
                "summary": {"total_detections": 0},
            }
            if debug:
                fb["_debug"] = {"model": self.model_name}
            return fb

    async def analyze_image_with_coordinates(
        self,
        image: Image.Image,
        target_texts: List[str] = ["PF100", "PF150"],
        *,
        debug: bool = False,
        target_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        図面画像内で指定されたキーワードを含む文字列を検出し、座標情報を取得する

        Args:
            image: PIL Imageオブジェクト
            target_texts: 検出対象のキーワードリスト（デフォルト: PF100, PF150）

        Returns:
            dict: 検出結果と座標情報
        """
        # target.png画像を読み込む
        import pathlib

        target_image_path = (
            pathlib.Path(__file__).parent.parent / "assets" / "images" / "target.png"
        )

        if not target_image_path.exists():
            raise FileNotFoundError(f"Target image not found: {target_image_path}")

        target_image = Image.open(target_image_path)

        coordinate_prompt = (
            "画像内（赤枠があれば枠内）の図面から、参照画像（target.png）と同一形状の記号のみを検出。"
            "回転やスケール差に頑健に対応し、誤検出を避ける。"
        )

        try:
            generation_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "object",
                    "properties": {
                        "detections": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "symbol_bbox": {
                                        "type": "array",
                                        "items": {"type": "number"}
                                    },
                                    "box_2d": {
                                        "type": "array",
                                        "items": {"type": "number"}
                                    },
                                    "confidence": {"type": "number"},
                                    "rationale": {"type": "string"},
                                    "matched_features": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                                "required": ["confidence"],
                            },
                        },
                        "summary": {
                            "type": "object",
                            "properties": {
                                "total_detections": {"type": "integer"}
                            },
                            "required": ["total_detections"],
                        },
                    },
                    "required": ["detections", "summary"],
                },
            )
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=self._build_contents(coordinate_prompt, image, target_image),
                    config=generation_config,
                )
            except Exception:
                fallback_prompt = (
                    coordinate_prompt
                    + "必ず次の形式のJSONのみを返してください: {\"detections\":[], \"summary\":{\"total_detections\":0}}"
                )
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=self._build_contents(fallback_prompt, image, target_image),
                )
            # Prefer structured parsed output
            detection_data = self._extract_structured(response)
            response_text = (getattr(response, "text", None) or "").strip()
            # 検出結果が空の場合は、より柔軟なプロンプトでリトライ
            if (
                not detection_data
                or not detection_data.get("detections")
                or detection_data.get("summary", {}).get("total_detections", 0) == 0
            ):
                fb = await self._retry_with_flexible_prompt(image, target_texts)
                if debug:
                    fb.setdefault("_debug", {})
                    fb["_debug"]["prompt"] = coordinate_prompt
                    fb["_debug"]["raw_response_text"] = response_text
                    fb["_debug"]["model"] = self.model_name
                return fb

                # Keep coordinates as [0,1000] normalized - do not convert to pixels
                # The detection data already contains normalized coordinates
                detection_data["coordinate_space"] = "normalized_1000"

                if debug:
                    detection_data.setdefault("_debug", {})
                    detection_data["_debug"]["prompt"] = coordinate_prompt
                    detection_data["_debug"]["raw_response_text"] = response_text or json.dumps(detection_data)
                    detection_data["_debug"]["model"] = self.model_name
                    detection_data["_debug"]["bbox_samples"] = debug_samples
                return detection_data

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
        # target.png画像を再度読み込む
        import pathlib

        target_image_path = (
            pathlib.Path(__file__).parent.parent / "assets" / "images" / "target.png"
        )
        target_image = Image.open(target_image_path)

        flexible_prompt = (
            "赤枠内の図面から、参照画像（target.png）に似た円形で中に十字の記号を検出。"
            "回転・スケール差に頑健。誤検出を避ける。"
        )

        try:
            generation_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "object",
                    "properties": {
                        "detections": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "symbol_bbox": {
                                        "type": "array",
                                        "items": {"type": "number"}
                                    },
                                    "box_2d": {
                                        "type": "array",
                                        "items": {"type": "number"}
                                    },
                                    "confidence": {"type": "number"},
                                },
                                "required": ["confidence"],
                            },
                        },
                        "summary": {
                            "type": "object",
                            "properties": {
                                "total_detections": {"type": "integer"}
                            },
                            "required": ["total_detections"],
                        },
                    },
                    "required": ["detections", "summary"],
                },
            )
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=self._build_contents(flexible_prompt, image, target_image),
                    config=generation_config,
                )
            except Exception:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=self._build_contents(flexible_prompt, image, target_image),
                )
            detection_data = self._extract_structured(response)
            if detection_data is not None:
                return detection_data
            response_text = (getattr(response, "text", None) or "")
            # 最後の手段として改良されたフォールバック分析
            return self._enhanced_fallback_analysis(response_text, target_texts, image)

        except Exception as e:
            return self._enhanced_fallback_analysis(
                f"エラー: {str(e)}", target_texts, image
            )

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
            pattern = re.compile(re.escape(text.replace("φ", "[φΦ]")), re.IGNORECASE)
            matches = pattern.findall(response_text)
            count = len(matches)

            # より柔軟なパターンマッチング
            if count == 0:
                # PF100, PF150 などの数字部分でも検索
                number_pattern = re.search(r"PF(\d+)", text, re.IGNORECASE)
                if number_pattern:
                    number = number_pattern.group(1)
                    flexible_pattern = f"PF{number}"
                    flexible_matches = re.findall(
                        flexible_pattern, response_text, re.IGNORECASE
                    )
                    count = len(flexible_matches)

            # キーワードごとのカウントを記録（動的）
            keyword_key = (
                f"{text.lower().replace('φ', 'phi').replace('Φ', 'phi')}_count"
            )
            summary[keyword_key] = count
            summary["total_detections"] += count

            # 画像サイズに基づいた推測座標を生成
            for i in range(count):
                # 画像を格子状に分割して配置
                cols = max(1, int((count**0.5)))
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
                        "fallback": True,
                    }
                )

        return {
            "detections": detections,
            "summary": summary,
            "fallback": True,
            "note": "推測ベースの検出結果",
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
            keyword_key = (
                f"{text.lower().replace('φ', 'phi').replace('Φ', 'phi')}_count"
            )
            summary[keyword_key] = count
            summary["total_detections"] += count

            # ダミー座標
            for i in range(count):
                detections.append(
                    {
                        "text": text,
                        "bbox": [100 + i * 200, 100 + i * 50, 100, 30],
                        "confidence": 0.5,
                        "fallback": True,
                    }
                )

        return {"detections": detections, "summary": summary, "fallback": True}

    async def analyze_pipe_shafts(
        self,
        pdf_bytes: bytes,
        *,
        debug: bool = False,
    ) -> Dict[str, Any]:
        """
        PDFドキュメントを解析してパイプシャフトの座標を検出する。

        Args:
            pdf_bytes: PDFファイルの生バイト列
            debug: デバッグ情報を付与する

        Returns:
            Dict[str, Any]: 構造化された検出結果
        """
        # 出力スキーマ（パイプシャフト検出用）
        detection_schema: Dict[str, Any] = {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "object",
                    "properties": {
                        "total_detections": {"type": "integer"},
                        "notes": {"type": "string"},
                    },
                    "required": ["total_detections"],
                },
                "pages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "page": {"type": "integer"},
                            "detections": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {
                                            "type": "string",
                                            "description": "パイプシャフトの種類（PF100, PF150など）",
                                        },
                                        "position": {
                                            "type": "object",
                                            "properties": {
                                                "x": {"type": "integer", "minimum": 0, "maximum": 1000},
                                                "y": {"type": "integer", "minimum": 0, "maximum": 1000},
                                            },
                                            "required": ["x", "y"],
                                        },
                                        "bbox": {
                                            "type": "array",
                                            "items": {"type": "integer", "minimum": 0, "maximum": 1000},
                                            "minItems": 4,
                                            "maxItems": 4,
                                            "description": "[x, y, width, height] normalized to [0,1000]",
                                        },
                                        "confidence": {"type": "number"},
                                        "description": {"type": "string"},
                                    },
                                    "required": ["position"],
                                },
                            },
                        },
                        "required": ["page", "detections"],
                    },
                },
            },
            "required": ["summary", "pages"],
        }

        prompt = (
            "あなたは建築図面解析の専門アシスタントです。"
            "このPDFは図面を表しています。各ページから以下を検出してください:\n"
            "- 100mm径の記号（PF100）\n"
            "- 150mm径の記号（PF150）\n"
            "- パイプシャフト（PS）の位置\n\n"
            "検出要件:\n"
            "- PF100/PF150は通常、円形で中に十字の線がある記号として表されます\n"
            "- PF100、PF150、またはPSという文字が近くにある場合があります\n"
            "- 座標は[0,1000]の範囲に正規化して返すこと。ページの左上を(0,0)、右下を(1000,1000)とする\n"
            "- position.x, position.y は検出対象の中心座標を[0,1000]の整数で記録\n"
            "- 矩形が分かる場合は bbox=[x,y,width,height] を[0,1000]の範囲で併記（オプション）\n"
            "- 検出がなければ該当ページのdetectionsは空配列\n"
            "- typeフィールドには \"PF100\", \"PF150\", \"PS\" のいずれかを設定\n"
            "- スキーマに沿ったJSONのみを返すこと（追加の説明文は返さない）\n"
        )

        try:
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    ],
                )
            ]

            generation_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=detection_schema,
            )

            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=generation_config,
                )
            except Exception:
                # 一部環境でstructured output未対応な場合のフォールバック
                fallback_prompt = (
                    prompt
                    + "\n\n必ず次の形式のJSONのみを返してください: "
                    + json.dumps(
                        {
                            "summary": {
                                "total_detections": 0,
                            },
                            "pages": [],
                        }
                    )
                )
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_text(text=fallback_prompt),
                                types.Part.from_bytes(
                                    data=pdf_bytes, mime_type="application/pdf"
                                ),
                            ],
                        )
                    ],
                )

            data = self._extract_structured(response)
            response_text = (getattr(response, "text", None) or "").strip()

            if not isinstance(data, dict) or not data:
                # テキストからのフォールバックJSONパース
                try:
                    data = json.loads(response_text) if response_text else None
                except Exception:
                    data = None

            if not isinstance(data, dict) or "summary" not in data or "pages" not in data:
                fb: Dict[str, Any] = {
                    "summary": {
                        "total_detections": 0,
                        "notes": "fallback: failed to parse structured output",
                    },
                    "pages": [],
                }
                if debug:
                    fb["_debug"] = {
                        "prompt": prompt,
                        "raw_response_text": response_text,
                        "model": self.model_name,
                    }
                return fb

            if debug:
                data.setdefault("_debug", {})
                try:
                    data["_debug"].update(
                        {
                            "prompt": prompt,
                            "raw_response_text": response_text or json.dumps(data),
                            "model": self.model_name,
                        }
                    )
                except Exception:
                    pass

            return data
        except Exception as e:
            raise Exception(f"パイプシャフト検出エラー: {str(e)}")

    def create_highlighted_image(
        self, original_image: Image.Image, detection_data: Dict[str, Any]
    ) -> Image.Image:
        """
        検出座標に沿ったシンプルな矩形ハイライトを描画して返す。

        ・Geminiが返した[0,1000]正規化座標をピクセル座標に変換
        ・[x, y, width, height] 矩形として半透明塗り + 赤枠
        ・追加の形状推定は行わない（ズレの原因を排除）
        """
        # 元画像をRGBAにして半透明オーバーレイを合成
        base = original_image.convert("RGBA")
        img_w, img_h = base.size
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        outline_color = (255, 0, 0, 255)  # 赤
        fill_color = (255, 255, 0, 64)    # 薄い黄の半透明

        def normalize_bbox(raw_bbox):
            # delegate to shared helper
            return self._to_pixel_bbox(raw_bbox, img_w, img_h)

        skipped = 0
        drawn = 0
        for det in (detection_data.get("detections") or []):
            bbox = normalize_bbox(
                det.get("symbol_bbox")
                or det.get("bbox")
                or ( {"box_2d": det.get("box_2d")} if det.get("box_2d") is not None else None )
                or det.get("box")
            )
            if not bbox:
                skipped += 1
                continue
            x, y, w, h = bbox
            line_w = max(2, int(min(img_w, img_h) * 0.003))
            draw.rectangle([x, y, x + w, y + h], fill=fill_color, outline=outline_color, width=line_w)
            drawn += 1

        try:
            log = logging.getLogger("pdf_highlight_api.gemini")
            total = len(detection_data.get("detections", [])) if isinstance(detection_data, dict) else 0
            log.info("Simple highlight drawn: total=%d drawn=%d skipped=%d", total, drawn, skipped)
        except Exception:
            pass

        return Image.alpha_composite(base, overlay)

    async def detect_target_image_in_pdf(
        self,
        pdf_bytes: bytes,
        custom_target_image: Image.Image = None,
        *,
        debug: bool = False,
    ) -> Dict[str, Any]:
        """
        PDFドキュメントを解析してターゲット画像と同じパターンを検出する。

        Args:
            pdf_bytes: PDFファイルの生バイト列
            custom_target_image: カスタムターゲット画像（未指定の場合はデフォルトのtarget.png）
            debug: デバッグ情報を付与する

        Returns:
            Dict[str, Any]: 構造化された検出結果
        """
        import pathlib
        from pdf2image import convert_from_bytes
        
        # ターゲット画像の準備
        if custom_target_image:
            target_image = custom_target_image
        else:
            # デフォルトのtarget.png画像を読み込む
            target_image_path = (
                pathlib.Path(__file__).parent.parent
                / "assets"
                / "images"
                / "target.png"
            )
            if not target_image_path.exists():
                raise FileNotFoundError(f"Target image not found: {target_image_path}")
            target_image = Image.open(target_image_path)
        
        # PDFを画像に変換
        images = convert_from_bytes(pdf_bytes, dpi=200)
        
        # 出力スキーマ
        detection_schema: Dict[str, Any] = {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "object",
                    "properties": {
                        "total_detections": {"type": "integer"},
                        "notes": {"type": "string"},
                    },
                    "required": ["total_detections"],
                },
                "pages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "page": {"type": "integer"},
                            "detections": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "position": {
                                            "type": "object",
                                            "properties": {
                                                "x": {"type": "integer", "minimum": 0, "maximum": 1000},
                                                "y": {"type": "integer", "minimum": 0, "maximum": 1000},
                                            },
                                            "required": ["x", "y"],
                                        },
                                        "confidence": {"type": "number"},
                                        "description": {"type": "string"},
                                    },
                                    "required": ["position"],
                                },
                            },
                        },
                        "required": ["page", "detections"],
                    },
                },
            },
            "required": ["summary", "pages"],
        }

        prompt = (
            "あなたは画像パターンマッチングの専門家です。\n"
            "2枚目以降の画像から、1枚目の参照画像（ターゲット画像）と同じパターンを探してください。\n\n"
            "参照画像の特徴:\n"
            "- 円形の中に十字の線がある記号\n"
            "- 建築図面で使用される記号\n\n"
            "検出要件:\n"
            "- 各ページで参照画像と同じ形状のパターンをすべて検出\n"
            "- 回転やサイズの違いがあっても検出すること\n"
            "- 座標は[0,1000]の範囲に正規化して返すこと。ページの左上を(0,0)、右下を(1000,1000)とする\n"
            "- position.x, position.y は検出対象の中心座標を[0,1000]の整数で記録\n"
            "- 検出がなければ該当ページのdetectionsは空配列\n"
            "- 1枚目は参照画像なので検出対象外（page 1から開始）\n"
            "- スキーマに沿ったJSONのみを返すこと\n"
        )

        try:
            # 画像パートを構築（ターゲット画像 + 各ページ）
            all_images = [target_image] + images
            
            contents = self._build_contents(prompt, *all_images)

            generation_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=detection_schema,
            )

            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=generation_config,
                )
            except Exception:
                # 構造化出力未対応の場合のフォールバック
                fallback_prompt = (
                    prompt
                    + "\n\n必ず次の形式のJSONのみを返してください: "
                    + json.dumps(
                        {
                            "summary": {
                                "total_detections": 0,
                            },
                            "pages": [],
                        }
                    )
                )
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=self._build_contents(fallback_prompt, *all_images),
                )

            data = self._extract_structured(response)
            response_text = (getattr(response, "text", None) or "").strip()

            if not isinstance(data, dict) or not data:
                try:
                    data = json.loads(response_text) if response_text else None
                except Exception:
                    data = None

            if not isinstance(data, dict) or "summary" not in data or "pages" not in data:
                fb: Dict[str, Any] = {
                    "summary": {
                        "total_detections": 0,
                        "notes": "fallback: failed to parse structured output",
                    },
                    "pages": [],
                }
                if debug:
                    fb["_debug"] = {
                        "prompt": prompt,
                        "raw_response_text": response_text,
                        "model": self.model_name,
                    }
                return fb

            if debug:
                data.setdefault("_debug", {})
                try:
                    data["_debug"].update(
                        {
                            "prompt": prompt,
                            "raw_response_text": response_text or json.dumps(data),
                            "model": self.model_name,
                        }
                    )
                except Exception:
                    pass

            return data
        except Exception as e:
            raise Exception(f"ターゲット画像検出エラー: {str(e)}")
