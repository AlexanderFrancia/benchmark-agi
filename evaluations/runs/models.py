from django.db import models
import uuid

class EvaluationRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_id = models.CharField(max_length=255)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="running")
    total_pairs = models.IntegerField(default=0)
    completed_pairs = models.IntegerField(default=0)
    global_correct = models.IntegerField(default=0)
    global_total = models.IntegerField(default=0)
    note = models.TextField(blank=True)

    @property
    def progress_pct(self):
        if self.total_pairs <= 0:
            return 0.0
        return round(self.completed_pairs * 100.0 / self.total_pairs, 2)

    @property
    def global_acc_pct(self):
        if self.global_total <= 0:
            return 0.0
        return round(self.global_correct * 100.0 / self.global_total, 2)

class EvaluationResult(models.Model):
    run = models.ForeignKey(EvaluationRun, on_delete=models.CASCADE, related_name="results")
    task_id = models.CharField(max_length=64)
    split = models.CharField(max_length=32)
    idx = models.IntegerField()
    status = models.CharField(max_length=32) 
    latency_s = models.FloatField(default=0.0)

    exact_match = models.FloatField(default=0.0)
    cell_accuracy = models.FloatField(default=0.0)
    correct = models.IntegerField(default=0)
    total = models.IntegerField(default=0)

    expected = models.JSONField(null=True, blank=True)
    predicted = models.JSONField(null=True, blank=True)
    raw_content = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["run", "task_id"]),
        ]
