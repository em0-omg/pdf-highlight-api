import os
from typing import List
import google.generativeai as genai
from PIL import Image


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