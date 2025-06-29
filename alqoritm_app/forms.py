# alqoritm_app/forms.py

from django import forms

class FileUploadForm(forms.Form):
    test_file = forms.FileField(label="Test Faylını Yüklə")
