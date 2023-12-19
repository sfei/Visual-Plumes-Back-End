from django.urls import path

from . import views

app_name = 'app'

urlpatterns = [
    path('', views.index, name='index'),
    path('run_analysis', views.run_analysis, name="run_analysis"),
    path('download_zip_archive/<str:model_run_id>', views.download_zip_archive, name="download_zip_archive")
]