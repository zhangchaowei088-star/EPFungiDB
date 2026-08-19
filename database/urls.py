from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('summary', views.SummaryViewSet, basename='summary')
router.register('kegg-pathway-index', views.KeggPathwayIndexViewSet, basename='kegg-pathway-index')
router.register('pathogenicity-overview', views.PathogenicityOverviewViewSet, basename='pathogenicity-overview')
router.register('samples', views.SampleViewSet, basename='samples')
router.register('basic-metadata', views.BasicMetadataRecordViewSet, basename='basic-metadata')
router.register('proteins', views.ProteinViewSet, basename='proteins')
router.register('kegg-pathway-members', views.KeggPathwayMemberViewSet, basename='kegg-pathway-members')
router.register('pathogenicity-features', views.ProteinPathogenicityFeatureViewSet, basename='pathogenicity-features')
router.register('annotation-sources', views.AnnotationSourceViewSet, basename='annotation-sources')

urlpatterns = [
    path('', include(router.urls)),
]
