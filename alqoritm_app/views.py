# alqoritm_app/views.py

from django.shortcuts import render
from django.http import FileResponse
from .forms import FileUploadForm
from .search_engine import run_analysis
import os
from django.conf import settings

def index(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            test_file = form.cleaned_data['test_file']
            print(f"📁 [1] İstifadəçi faylı yüklədi: {test_file.name}")

            test_file_path = os.path.join(settings.MEDIA_ROOT, test_file.name)
            with open(test_file_path, 'wb+') as destination:
                for chunk in test_file.chunks():
                    destination.write(chunk)
            print(f"💾 [2] Fayl yadda saxlanıldı: {test_file_path}")    

            master_path = os.path.join(settings.BASE_DIR, 'MASTER_DATABASE_FINAL.xlsx')
            print(f"📚 [3] Master fayl yolu: {master_path}")
            try:
                print(f"🚀 [4] Analiz başlayır...")
                output_path = run_analysis(master_path, test_file_path, settings.MEDIA_ROOT)
            #    print(f"✅ [5] Analiz bitdi, fayl hazır: {output_path}")

                # Excel faylını browserə göndər
                return FileResponse(open(output_path, 'rb'), as_attachment=True, filename=os.path.basename(output_path))
            except Exception as e:
                print(f"❌ [Xəta baş verdi]: {e}")
                return render(request, 'alqoritm_app/index.html', {'form': form, 'error': str(e)})
    else:
        form = FileUploadForm()
    return render(request, 'alqoritm_app/index.html', {'form': form})
