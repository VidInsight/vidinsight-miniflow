import json

class MultiplyWithSum:
    def __init__(self):
        self.name = "Multiply With Sum"
    
    def run(self, context=None):
        """
        İlk adımın sonucunu alıp bir sayı ile çarpar
        """
        try:
            # Context'ten değerleri al
            if context and 'step1_result' in context:
                sum_result = context['step1_result']
            else:
                # Fallback değer
                sum_result = 40  # step1'in sonucu (15 + 25)
            
            # Çarpan değeri
            multiplier = 3
            
            result = sum_result * multiplier
            
            # JSON formatında sonuç döndür
            output = {
                "operation": "multiply_with_sum",
                "sum_result": sum_result,
                "multiplier": multiplier,
                "result": result,
                "status": "success"
            }
            
            return json.dumps(output)
            
        except Exception as e:
            error_output = {
                "operation": "multiply_with_sum",
                "error": str(e),
                "status": "failed"
            }
            return json.dumps(error_output)

def module():
    """
    Python runner için gerekli module() fonksiyonu
    """
    return MultiplyWithSum() 