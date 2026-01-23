from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ExampleItem
from .serializers import ExampleItemSerializer
from .services import generate_random_number, check_system_status

class ExampleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Example Items.
    """
    queryset = ExampleItem.objects.all()
    serializer_class = ExampleItemSerializer

    @action(detail=False, methods=['post'])
    def generate_random(self, request):
        """
        Generate a random number via API.
        """
        min_val = int(request.data.get('min', 0))
        max_val = int(request.data.get('max', 100))
        result = generate_random_number(min_val, max_val)
        return Response({'result': result})

    @action(detail=False, methods=['get'])
    def system_status(self, request):
        """
        Check system status via API.
        """
        status = check_system_status()
        return Response(status)
