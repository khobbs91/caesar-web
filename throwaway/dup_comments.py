from review.models import Comment
from django.db.models import Count

dupes = Comment.objects.filter(chunk__file__submission__milestone__assignment__semester__id=7L)
dupes.values('text').annotate(num_repeats=Count('text')).filter(num_repeats__gt=1).order_by('-num_repeats')



# comments_in_milestone = Comment.objects.filter(chunk__file__submission__milestone__assignment__semester__id=7L)
# dupes = comments_in_milestone.values('text').annotate(num_repeats=Count('text')).order_by().filter(num_repeats__gt=1)
# comments_in_milestone.objects.filter(text__in=[item['text'] for item in dupes])



# comments_in_milestone = Comment.objects.filter(chunk__file__submission__milestone__assignment__semester__id=7L)
# dupes = comments_in_milestone.values('text').annotate(Count('id')).values('text').order_by().filter(id__count__gt=1)
# comments_in_milestone.objects.filter(text__in=dupes)