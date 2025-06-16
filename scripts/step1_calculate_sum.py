import json

class CalculateSum:
    def __init__(self):
        self.name = "Calculate Sum"
    
    def run(self, context=None):
        """
        İki sayıyı toplar ve JSON formatında sonuç döner
        """
        try:
            # Test için sabit değerler
            a = 15
            b = 25
            
            result = a + b
            
            # JSON formatında sonuç döndür
            output = {
                "operation": "sum",
                "input_a": a,
                "input_b": b,
                "result": result,
                "status": "success"
            }
            
            return json.dumps(output)
            
        except Exception as e:
            error_output = {
                "operation": "sum",
                "error": str(e),
                "status": "failed"
            }
            return json.dumps(error_output)

def module():
    """
    Python runner için gerekli module() fonksiyonu
    """
    return CalculateSum() 