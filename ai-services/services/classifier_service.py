class ClassifierService:
    def classify(self, text: str, file_name: str = "") -> str:
        haystack = f"{file_name}\n{text[:6000]}".lower()
        if any(term in haystack for term in ["claim form", "claimant", "date of accident", "claim no"]):
            return "claim"
        if any(term in haystack for term in ["invoice", "bill no", "amount payable", "gst"]):
            return "invoice"
        if any(term in haystack for term in ["prescription", "diagnosis", "medicine", "clinical"]):
            return "medical"
        if any(term in haystack for term in ["aadhaar", "pan card", "kyc"]):
            return "kyc"
        if any(term in haystack for term in ["policy number", "sum insured", "premium", "exclusions", "waiting period"]):
            return "policy"
        return "policy"
