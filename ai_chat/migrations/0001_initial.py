# Generated manually for local discussion knowledge indexing.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("home", "0095_alter_allschedules_daten_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlaceKnowledgeEmbedding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_type", models.CharField(max_length=100)),
                ("source_id", models.CharField(max_length=100)),
                ("title", models.CharField(blank=True, max_length=255)),
                ("text", models.TextField()),
                ("embedding", models.JSONField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("content_hash", models.CharField(max_length=64)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "place",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="knowledge_embeddings",
                        to="home.places_v2",
                    ),
                ),
            ],
            options={
                "ordering": ["place_id", "source_type", "source_id"],
                "indexes": [
                    models.Index(fields=["place", "source_type"], name="ai_chat_pla_place_i_b50fbc_idx"),
                    models.Index(fields=["place", "content_hash"], name="ai_chat_pla_place_i_fa449d_idx"),
                ],
                "unique_together": {("place", "source_type", "source_id")},
            },
        ),
    ]
