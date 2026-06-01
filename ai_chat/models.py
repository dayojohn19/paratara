from django.db import models


class PlaceKnowledgeEmbedding(models.Model):
    place = models.ForeignKey(
        "home.Places_v2",
        on_delete=models.CASCADE,
        related_name="knowledge_embeddings",
    )
    source_type = models.CharField(max_length=100)
    source_id = models.CharField(max_length=100)
    title = models.CharField(max_length=255, blank=True)
    text = models.TextField()
    embedding = models.JSONField()
    metadata = models.JSONField(default=dict, blank=True)
    content_hash = models.CharField(max_length=64)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("place", "source_type", "source_id")
        indexes = [
            models.Index(fields=["place", "source_type"]),
            models.Index(fields=["place", "content_hash"]),
        ]
        ordering = ["place_id", "source_type", "source_id"]

    def __str__(self):
        return f"{self.place}: {self.source_type}:{self.source_id}"

