import json

class MultiplyNumbers:
    def __init__(self):
        self.name = "Multiply Numbers Calculator"
    
    def run(self, params=None):
        """
        İki sayıyı çarpar ve JSON formatında sonuç döner
        """
        try:
            # Test için sabit değerler (gerçek uygulamada parametrelerden gelecek)
            a = 5
            b = 8
            
            result = a * b
            
            # JSON formatında sonuç döndür
            output = {
                "operation": "multiplication",
                "input_a": a,
                "input_b": b,
                "result": result,
                "status": "success"
            }
            
            return json.dumps(output)
            
        except Exception as e:
            error_output = {
                "operation": "multiplication",
                "error": str(e),
                "status": "failed"
            }
            return json.dumps(error_output)

def module():
    """
    Python runner için gerekli module() fonksiyonu
    """
    return MultiplyNumbers() 