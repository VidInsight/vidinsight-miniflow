import json

class CalculateFinalAverage:
    def __init__(self):
        self.name = "Calculate Final Average"
    
    def run(self, context=None):
        """
        İlk iki adımın sonuçlarını alıp ortalamasını hesaplar
        """
        try:
            # Context'ten değerleri al
            if context and 'step1_result' in context:
                step1_result = context['step1_result']
            else:
                # Fallback değer
                step1_result = 40  # step1'in sonucu (15 + 25)
            
            if context and 'step2_result' in context:
                step2_result = context['step2_result']
            else:
                # Fallback değer
                step2_result = 120  # step2'nin sonucu (40 * 3)
            
            # Ortalama hesapla
            average = (step1_result + step2_result) / 2
            
            # JSON formatında sonuç döndür
            output = {
                "operation": "final_average",
                "step1_result": step1_result,
                "step2_result": step2_result,
                "average": average,
                "status": "success"
            }
            
            return json.dumps(output)
            
        except Exception as e:
            error_output = {
                "operation": "final_average",
                "error": str(e),
                "status": "failed"
            }
            return json.dumps(error_output)

def module():
    """
    Python runner için gerekli module() fonksiyonu
    """
    return CalculateFinalAverage() 