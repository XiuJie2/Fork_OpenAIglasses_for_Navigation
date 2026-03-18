from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import (
    SiteSettings, HomeContent, ProductPageContent,
    DownloadPageContent, PurchasePageContent, TeamPageContent,
)
from .serializers import (
    SiteSettingsSerializer, HomeContentSerializer,
    ProductPageContentSerializer, DownloadPageContentSerializer,
    PurchasePageContentSerializer, TeamPageContentSerializer,
)


class SiteContentView(APIView):
    """回傳所有網站內容，按頁面分組"""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'site': SiteSettingsSerializer(SiteSettings.load()).data,
            'home': HomeContentSerializer(HomeContent.load()).data,
            'product': ProductPageContentSerializer(ProductPageContent.load()).data,
            'download': DownloadPageContentSerializer(DownloadPageContent.load()).data,
            'purchase': PurchasePageContentSerializer(PurchasePageContent.load()).data,
            'team': TeamPageContentSerializer(TeamPageContent.load()).data,
        })
