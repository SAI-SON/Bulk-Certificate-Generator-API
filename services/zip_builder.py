import os
import zipfile
from tempfile import NamedTemporaryFile
from django.conf import settings

class ZipBuilder:
    """
    Utility to build ZIP archives of certificates.
    """
    
    @staticmethod
    def build_certificates_zip(batch):
        """
        Creates a ZIP file containing all successful certificates for a batch.
        Returns the path to the temporary ZIP file.
        """
        successful_certs = batch.certificates.filter(status="generated")
        if not successful_certs.exists():
            return None
            
        temp_zip = NamedTemporaryFile(delete=False, suffix=".zip", prefix=f"batch_{batch.id}_")
        
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            for cert in successful_certs:
                if cert.generated_file and os.path.exists(cert.generated_file.path):
                    # Store in the zip with the base filename
                    zf.write(cert.generated_file.path, arcname=os.path.basename(cert.generated_file.name))
                    
        return temp_zip.name
