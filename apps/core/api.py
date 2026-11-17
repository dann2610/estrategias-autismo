"""API REST de solo lectura. Únicamente expone contenido aprobado o pictogramas visibles."""
from rest_framework import generics, serializers

from apps.practice.models import Activity, Pictogram


class ActivitySerializer(serializers.ModelSerializer):
    kind = serializers.CharField(source="get_kind_display")
    ficha = serializers.CharField(source="get_absolute_url")

    class Meta:
        model = Activity
        fields = ("id", "title", "description", "kind", "age_range", "duration", "place", "objective", "ficha")


class PictogramSerializer(serializers.ModelSerializer):
    src = serializers.CharField()

    class Meta:
        model = Pictogram
        fields = ("id", "code", "label", "category", "src", "credit", "license")


class ActivityList(generics.ListAPIView):
    serializer_class = ActivitySerializer

    def get_queryset(self):
        qs = Activity.objects.public()
        for f in ("kind", "age_range", "place", "duration"):
            if self.request.query_params.get(f):
                qs = qs.filter(**{f: self.request.query_params[f]})
        return qs.order_by("title")


class PictogramList(generics.ListAPIView):
    serializer_class = PictogramSerializer
    pagination_class = None
    queryset = Pictogram.objects.filter(active=True)
