import json

class CalculateAverage:
    def __init__(self):
        self.name = "Average Calculator"
    
    def run(self):
        """
        Sayıların ortalamasını hesaplar ve JSON formatında sonuç döner
        """
        try:
            # Test için sabit değerler (gerçek uygulamada parametrelerden gelecek)
            numbers = [15, 25, 35, 45, 55]
            
            if not numbers:
                raise ValueError("Number list cannot be empty")
            
            total = sum(numbers)
            count = len(numbers)
            average = total / count
            
            # JSON formatında sonuç döndür
            output = {
                "operation": "average",
                "input_numbers": numbers,
                "total": total,
                "count": count,
                "result": average,
                "status": "success"
            }
            
            return json.dumps(output)
            
        except Exception as e:
            error_output = {
                "operation": "average",
                "error": str(e),
                "status": "failed"
            }
            return json.dumps(error_output)

def module():
    """
    Python runner için gerekli module() fonksiyonu
    """
    return CalculateAverage() 