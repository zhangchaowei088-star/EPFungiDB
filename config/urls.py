"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from database.views import antismash_report, bioassays, dashboard, gene_detail, gene_families, genes, genome_detail, genomes, kegg, literature, species

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('species/', species, name='species'),
    path('genomes/', genomes, name='genomes'),
    path('genomes/<str:sample_id>/antismash/', antismash_report, name='antismash_report'),
    path('genomes/<str:sample_id>/antismash/<path:asset_path>', antismash_report, name='antismash_report_asset'),
    path('genomes/<str:sample_id>/', genome_detail, name='genome_detail'),
    path('genes/', genes, name='genes'),
    path('kegg/', kegg, name='kegg'),
    path('gene-families/', gene_families, name='gene_families'),
    path('bioassays/', bioassays, name='bioassays'),
    path('literature/', literature, name='literature'),
    path('genes/<path:protein_uid>/', gene_detail, name='gene_detail'),
    path('api/', include('database.urls')),
    path('admin/', admin.site.urls),
]
