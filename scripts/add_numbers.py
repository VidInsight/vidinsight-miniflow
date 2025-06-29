import json

class AddNumbers:
    def __init__(self):
        self.name = "Add Numbers Calculator"
    
    def run(self, params=None):
        """
        İki sayıyı toplar ve JSON formatında sonuç döner
        """
        try:
            # Parametreleri al, yoksa varsayılan değerler kullan
            if params and isinstance(params, dict):
                a = params.get('a', 10)
                b = params.get('b', 20)
            else:
                a = 10
                b = 20
            
            result = a + b
            
            # JSON formatında sonuç döndür
            output = {
                "operation": "addition",
                "input_a": a,
                "input_b": b,
                "result": result,
                "status": "success"
            }
            
            return json.dumps(output)
            
        except Exception as e:
            error_output = {
                "operation": "addition",
                "error": str(e),
                "status": "failed"
            }
            return json.dumps(error_output)

def module():
    """
    Python runner için gerekli module() fonksiyonu
    """
    return AddNumbers() 