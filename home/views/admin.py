from typing import Optional

from django.shortcuts import redirect, render
from django.views.generic.list import View
from django.db.models import QuerySet, Q
from django.http import JsonResponse
from django.template.context_processors import csrf

from crispy_forms.utils import render_crispy_form

from discord_webhook import DiscordWebhook # https://pypi.org/project/discord-webhook/
from discord_webhook.webhook import DiscordEmbed

from home.models import Review, Professor, ProfessorCourse, Grade, User
from home.mail import send_email
from home.utils import AdminAction, slug_in_use_err
from home.tables.reviews_table import UnverifiedReviewsTable
from home.tables.basic import ProfessorsTable
from home.forms.admin_forms import ProfessorMergeForm, ProfessorMergeFormModal, ProfessorSlugForm, ProfessorUpdateForm
from planetterp import config

class Admin(View):
    BAD_REQUEST = 400

    def get(self, request):
        user = request.user

        if not (user.is_staff or user.is_superuser):
            return redirect('/')

        reviews = Review.objects.pending
        professors = Professor.objects.pending

        reviews_table = UnverifiedReviewsTable(reviews, request)
        professors_table = ProfessorsTable(professors, request)
        merge_professor_form = ProfessorMergeForm(request, use_large_inputs=True)

        context = {
            "reviews": reviews,
            "professors": professors,
            "reviews_table": reviews_table,
            "professors_table": professors_table,
            "merge_professor_form": merge_professor_form
        }

        return render(request, "admin.html", context)

    def post(self, request):
        data = request.POST
        action_type = AdminAction(data["action_type"])

        user = request.user
        if not (user.is_staff or user.is_superuser):
            return redirect('/')

        if action_type is AdminAction.REVIEW_VERIFY:
            verified_status = Review.Status(data["verified"])
            review_id = int(data["review_id"])
            return self.verify_review(review_id, verified_status, user)

        if action_type is AdminAction.REVIEW_HELP:
            channel_url = config.discord_webhook_help_url
            review = Review.objects.select_related().get(pk=int(data["review_id"]))
            professor = review.professor
            professor_id = professor.id
            grade = review.grade if review.grade else "N/A"
            review_text = review.content

            if channel_url:
                webhook = DiscordWebhook(url=channel_url)
                embed = DiscordEmbed(title=professor.name, description="\n", url="https://planetterp.com/admin")
                course = review.course.name if review.course else "N/A"
                review_text = review_text if len(review_text) <= 1000 else review_text[:1000] + "..."

                embed.add_embed_field(name="Reviewer", value=review.user.username, inline=True)
                embed.add_embed_field(name="Course", value=course, inline=True)
                embed.add_embed_field(name="Grade", value=grade, inline=True)
                embed.add_embed_field(name="Review", value=review_text, inline=False)

                webhook.add_embed(embed)
                webhook.execute()
            return JsonResponse({"response": "Help request sent", "success": True})

        elif action_type is AdminAction.PROFESSOR_VERIFY:
            verified_status = Professor.Status(data["verified"])
            professor_id = int(data["professor_id"])
            professor = Professor.objects.filter(pk=professor_id).first()

            if professor and professor.slug:
                slug = professor.slug
            else:
                slug = None

            return self.verify_professor(verified_status, slug, professor, request)

        elif action_type is AdminAction.PROFESSOR_EDIT:
            professor_id = data["hidden_professor_id"]
            professor = Professor.objects.get(pk=professor_id)
            initial_data = {
                "name": professor.name,
                "slug": professor.slug,
                "type": professor.type,
                "hidden_professor_id": professor.pk
            }
            form = ProfessorUpdateForm(professor, data=request.POST, initial=initial_data)

            context = {
                "professor_type": professor.type,
                "name": None,
                "slug": None,
                "type": None
            }

            if form.has_changed():
                if form.is_valid():
                    if 'name' in form.changed_data:
                        context['name'] = professor.name = form.cleaned_data['name']
                    if 'slug' in form.changed_data:
                        context['slug'] = professor.slug = form.cleaned_data['slug']
                    if 'type' in form.changed_data:
                        context['type'] = professor.type = form.cleaned_data['type']

                    professor.save()

                    context["success"] = True
                    form = ProfessorUpdateForm(professor)
                else:
                    context["success"] = False

                    if 'name' in form.changed_data:
                        context['name'] = form.errors.pop("name", "valid")
                    if 'slug' in form.changed_data:
                        context['slug'] = form.errors.pop("slug", "valid")
                    if 'type' in form.changed_data:
                        context['type'] = form.errors.pop("type", "valid")

            return JsonResponse(context)

        elif action_type is AdminAction.PROFESSOR_MERGE:
            if 'professor' in data['source_page']:
                form = ProfessorMergeFormModal(request, data=request.POST)
            else:
                form = ProfessorMergeForm(request, use_large_inputs=True, data=request.POST)

            ctx = {}
            ctx.update(csrf(request))
            context = {
                "success": False
            }

            if form.is_valid():
                subject_id = form.cleaned_data['subject_id']
                target_id = form.cleaned_data['target_id']
                merge_subject = Professor.objects.get(pk=subject_id)
                merge_target = Professor.objects.get(pk=target_id)

                ProfessorCourse.objects.filter(professor__id=subject_id).update(professor=merge_target)
                Review.objects.filter(professor__id=subject_id).update(professor=merge_target)
                Grade.objects.filter(professor__id=subject_id).update(professor=merge_target)
                context['success'] = True
                context["target_slug"] = merge_target.slug
                merge_subject.delete()

            context['form'] = render_crispy_form(form, form.helper, context=ctx)
            return JsonResponse(context)

        elif action_type is AdminAction.PROFESSOR_DELETE:
            professor_id = int(data["professor_id"])
            professor_type = str(data["professor_type"])
            has_reviews = Review.objects.filter(professor__id=professor_id).exists()
            has_grades = Grade.objects.filter(professor__id=professor_id).exists()
            has_courses = ProfessorCourse.objects.filter(professor__id=professor_id).exists()
            response = {
                "id" : professor_id,
                "type": professor_type,
            }

            professor_data = []
            if has_reviews:
                professor_data.append("review")
            if has_grades:
                professor_data.append("grade")
            if has_courses:
                professor_data.append("course")

            if any(professor_data):
                if len(professor_data) > 1:
                    professor_data[-1] = "and" + professor_data[-1]

                response["error_msg"] = (
                    f"This {professor_type} still has {', '.join(professor_data)} data and cannot be "
                    f"deleted! Please merge this {professor_type} then try again."
                )
            else:
                Professor.objects.filter(pk=professor_id).delete()
                response["success_msg"] = "deleted"

            return JsonResponse(response)

        elif action_type is AdminAction.PROFESSOR_SLUG:
            professor_id = int(data["professor_id"])
            professor = Professor.objects.filter(pk=professor_id).first()
            form = ProfessorSlugForm(professor, data=request.POST)

            ctx = {}
            context = {
                "id": professor.id,
                "success": False
            }
            ctx.update(csrf(request))

            if form.is_valid():
                professor.slug = form.cleaned_data['slug']
                professor.status = Professor.Status.VERIFIED
                professor.save()

                form = ProfessorSlugForm(professor)
                context['success'] = True
                context['type'] = professor.type

            context['form'] = render_crispy_form(form, form.helper, context=ctx)
            return JsonResponse(context)


    def not_found_err(self, type_: str):
        return f"{type_} not found"

    def verify_review(self, review_id: int, verified_status: Review.Status, user: User):
        review = Review.objects.filter(pk=review_id).first()
        if not review:
            response = {
                "error_msg": self.not_found_err("Review"),
                "success": False
            }
            return JsonResponse(response)

        review.status = verified_status
        review.updater = user
        review.save()

        reviewer = review.user
        professor = review.professor
        professor_status = Professor.Status(professor.status)
        response = {
            "success_msg": None,
            "verified_status": 'unverified' if verified_status is Review.Status.PENDING else verified_status.value,
            "success": True,
            "review_id": review.pk
        }

        if professor_status is Professor.Status.PENDING:
            response['success_msg'] = (
                " however the review is associated with"
                f"an unverified {professor.type}. Please verify {professor.type}"
                f" {professor.name} ({professor.pk}) as soon as possible."
            )

        if reviewer:
            self.validate_email(verified_status, professor, reviewer)

        return JsonResponse(response)

    def verify_professor(self, verified_status: Professor.Status, slug: Optional[str], professor: Professor, request):
        response = {
            "id" : professor.pk,
            "type": professor.type,
            "success_msg": None,
            "error_msg": None,
            "form": None
        }

        if verified_status is Professor.Status.VERIFIED:
            if not professor:
                response["error_msg"] = self.not_found_err("Professor")
                return JsonResponse(response)
            if not professor.slug and slug is None:
                # Attempt to create slug automatically
                split_name = str(professor.name).split(" ")
                first_name = split_name[0].lower().strip()
                last_name = split_name[-1].lower().strip()

                query = Professor.objects.filter(
                    (Q(name__istartswith=first_name) & Q(name__iendswith=last_name)) |
                    Q(slug=last_name),
                    status=verified_status)

                if query.exists():
                    response["error_msg"] = (
                    "This professor is likely a"
                        f"duplicate because a similar {professor.type}"
                        "already exists. Please reject or delete this professor."
                    )

                    return JsonResponse(response)

                modal_msg = None
                if len(split_name) > 2:
                    modal_msg = (
                        f"The name '{professor.name}' is too long and"
                        "can't be slugged automatcially. Please enter a slug below."
                    )

                if modal_msg:
                    # Create the modal form to manualy enter
                    #   a slug and add it to the response. The
                    #   form creates the modal, though it's
                    #   actually summoned from admin-action.js
                    ctx = {}
                    ctx.update(csrf(request))
                    form = ProfessorSlugForm(professor, modal_title=modal_msg)
                    response["form"] = render_crispy_form(form, form.helper, context=ctx)
                    return JsonResponse(response)

                professor.slug = last_name
        else:
            professor.slug = None
            if verified_status is Professor.Status.REJECTED:
                reviews = Review.objects.filter(professor__id=professor.pk)
                reviews.update(status=verified_status)

        professor.status = verified_status
        professor.save()
        response["success_msg"] = "unverified" if verified_status is Professor.Status.PENDING else verified_status.value

        return JsonResponse(response)

    def validate_email(self, verified: bool, professor: Professor, user: User):
        reviewer_email = user.email

        if reviewer_email and user.send_review_email:
            message = (
                f"Your review for <a href=\"https://planetterp.com/professor/{professor.slug}\">{professor.name}"
                f"</a> has been {'approved' if verified else 'rejected'}.<br />"
                "<br /> If you would no longer like to receive review"
                "verification emails, you can disable them on"
                '<a href="https://planetterp.com/profile#settings">'
                "your profile settings page</a>."
                )

            send_email(reviewer_email, f"Planetterp Review {'Approved' if verified else 'Rejected'}", message)
