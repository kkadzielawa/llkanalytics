from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="comment",
            name="submitter_hash",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                max_length=64,
            ),
        ),
        migrations.AddIndex(
            model_name="comment",
            index=models.Index(
                fields=["submitter_hash", "created"],
                name="blog_comment_submitter_idx",
            ),
        ),
        migrations.AlterField(
            model_name="comment",
            name="active",
            field=models.BooleanField(default=False),
        ),
    ]
