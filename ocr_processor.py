#!/usr/bin/env python3
"""
Receipt OCR Processor
Extract transaction data from receipt images using Tesseract OCR
"""

import pytesseract
import cv2
import json
import re
from PIL import Image
from datetime import datetime
from pathlib import Path
import tempfile

class ReceiptOCR:
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "receipt_ocr"
        self.temp_dir.mkdir(exist_ok=True)
    
    def preprocess_image(self, image_path):
        """Preprocess image untuk better OCR accuracy"""
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(thresh, h=10)
        
        # Save preprocessed image
        temp_path = self.temp_dir / f"preprocessed_{datetime.now().timestamp()}.png"
        cv2.imwrite(str(temp_path), denoised)
        
        return temp_path
    
    def extract_text(self, image_path):
        """Extract text from receipt image"""
        try:
            # Preprocess image
            processed_path = self.preprocess_image(image_path)
            
            # OCR dengan Tesseract
            text = pytesseract.image_to_string(
                str(processed_path),
                lang='eng',
                config='--psm 6 --oem 3'
            )
            
            return text.strip()
        except Exception as e:
            raise Exception(f"OCR failed: {str(e)}")
    
    def parse_receipt(self, text):
        """Parse OCR text dan extract transaction data"""
        result = {
            'merchant': None,
            'amount': None,
            'date': None,
            'items': [],
            'raw_text': text
        }
        
        lines = text.split('\n')
        
        # Extract amount (common patterns: Rp XXX,XXX / Total: XXX / Subtotal: XXX)
        amount_patterns = [
            r'(?:Rp|RP|rp)\s*[\.,\s]*(\d+(?:[.,]\d+)*)',
            r'(?:Total|TOTAL|total)\s*[:\-]?\s*[\.,\s]*(\d+(?:[.,]\d+)*)',
            r'(?:SUBTOTAL|Subtotal)\s*[:\-]?\s*[\.,\s]*(\d+(?:[.,]\d+)*)',
            r'(\d+(?:[.,]\d+)*)\s*(?:Rp|RP|rp)?(?:\s|$)',
        ]
        
        for line in lines:
            for pattern in amount_patterns:
                match = re.search(pattern, line)
                if match and result['amount'] is None:
                    amount_str = match.group(1).replace('.', '').replace(',', '')
                    try:
                        result['amount'] = int(amount_str)
                        break
                    except:
                        continue
        
        # Extract date (common patterns: DD/MM/YYYY, DD-MM-YYYY, DDMMYY)
        date_patterns = [
            r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})',
            r'(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})',
        ]
        
        for line in lines:
            for pattern in date_patterns:
                match = re.search(pattern, line)
                if match and result['date'] is None:
                    try:
                        groups = match.groups()
                        if len(groups[2]) == 4:  # YYYY format
                            result['date'] = f"{groups[2]}-{groups[1]}-{groups[0]}"
                        else:  # YY format
                            year = f"20{groups[2]}"
                            result['date'] = f"{year}-{groups[1]}-{groups[0]}"
                        break
                    except:
                        continue
        
        # Extract merchant name (usually first non-empty line or contains keywords)
        merchant_keywords = ['cafe', 'restaurant', 'shop', 'store', 'mart', 'supermarket', 'toko', 'resto', 'warung']
        
        for line in lines:
            line_clean = line.strip()
            if len(line_clean) > 3 and len(line_clean) < 100:
                if any(kw in line_clean.lower() for kw in merchant_keywords):
                    result['merchant'] = line_clean
                    break
        
        # If no merchant found, use first substantial line
        if not result['merchant']:
            for line in lines:
                line_clean = line.strip()
                if len(line_clean) > 5 and len(line_clean) < 100:
                    result['merchant'] = line_clean
                    break
        
        # Extract items (lines with numbers that look like prices)
        item_pattern = r'^(.+?)\s*[\.,\s]*(\d+(?:[.,]\d+)*)\s*$'
        for line in lines:
            line_clean = line.strip()
            if len(line_clean) > 5:
                match = re.search(item_pattern, line_clean)
                if match:
                    try:
                        item_name = match.group(1).strip()
                        item_price = match.group(2).replace('.', '').replace(',', '')
                        result['items'].append({
                            'name': item_name,
                            'price': int(item_price)
                        })
                    except:
                        pass
        
        return result
    
    def process_receipt(self, image_path):
        """Main function to process receipt image"""
        try:
            # Extract text
            text = self.extract_text(image_path)
            
            # Parse receipt data
            data = self.parse_receipt(text)
            
            return {
                'status': 'success',
                'data': data,
                'confidence': self._calculate_confidence(data)
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'confidence': 0
            }
    
    def _calculate_confidence(self, data):
        """Calculate OCR confidence score"""
        confidence = 0
        if data['amount']:
            confidence += 30
        if data['date']:
            confidence += 25
        if data['merchant']:
            confidence += 25
        if len(data['items']) > 0:
            confidence += 20
        return min(confidence, 100)

# CLI interface
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 ocr_processor.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    processor = ReceiptOCR()
    result = processor.process_receipt(image_path)
    
    print(json.dumps(result, indent=2))
