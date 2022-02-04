from typing import Optional

from django.shortcuts import render
from django.views import View
from django.db.models import Q
from django.http import JsonResponse
from django.template.context_processors import csrf
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse

from crispy_forms.utils import render_crispy_form
from discord_webhook import DiscordWebhook, DiscordEmbed

from home.models import Review, Professor, ProfessorCourse, Grade, User
from home.utils import AdminAction
from home.tables.reviews_table import UnverifiedReviewsTable
from home.tables.basic import ProfessorsTable
from home.forms.admin_forms import (ProfessorMergeForm, ProfessorSlugForm,
    ProfessorUpdateForm, ReviewActionForm)
from home.utils import send_email
from planetterp import config

class Admin(UserPassesTestMixin, View):

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        reviews = (
            Review.pending
            .select_related("professor", "course", "user")
            .all()
        )
        professors = Professor.pending.all()

        reviews_table = UnverifiedReviewsTable(reviews, request)
        professors_table = ProfessorsTable(professors, request)
        review_action_form = ReviewActionForm()

        context = {
            "reviews": reviews,
            "professors": professors,
            "reviews_table": reviews_table,
            "professors_table": professors_table,
            "review_action_form": review_action_form
        }

        context.update(csrf(request))

        return render(request, "admin.html", context)

    def post(self, request):
        data = request.POST
        action_type = AdminAction(data["action_type"])
        user = request.user

        if action_type is AdminAction.REVIEW_VERIFY:
            verified_status = Review.Status(data["verified"])
            review_id = int(data["review_id"])
            return self.verify_review(review_id, verified_status, user)

        if action_type is AdminAction.REVIEW_HELP:
            channel_url = config.WEBHOOK_URL_HELP
            review = Review.unfiltered.select_related().get(pk=int(data["review_id"]))
            professor = review.professor
            professor_id = professor.id
            grade = review.grade if review.grade else "N/A"
            review_text = review.content

            if channel_url:
                webhook = DiscordWebhook(url=channel_url)
                admin_url = request.build_absolute_uri(reverse("admin"))
                embed = DiscordEmbed(title=professor.name, description="\n", url=admin_url)
                course = review.course.name if review.course else "N/A"
                review_text = review_text if len(review_text) <= 1000 else review_text[:1000] + "..."
                username = "Anonymous" if review.anonymous else review.user.username

                embed.add_embed_field(name="Reviewer", value=username, inline=True)
                embed.add_embed_field(name="Course", value=course, inline=True)
                embed.add_embed_field(name="Grade", value=grade, inline=True)
                embed.add_embed_field(name="Review", value=review_text, inline=False)

                webhook.add_embed(embed)
                webhook.execute()
            return JsonResponse({"response": "Help request sent", "success": True})

        elif action_type is AdminAction.PROFESSOR_VERIFY:
            verified_status = Professor.Status(data["verified"])
            professor_id = int(data["professor_id"])
            professor = Professor.unfiltered.filter(pk=professor_id).first()

            if professor and professor.slug:
                slug = professor.slug
            else:
                slug = None

            return self.verify_professor(verified_status, slug, professor, request)

        elif action_type is AdminAction.PROFESSOR_EDIT:
            professor_id = data["hidden_professor_id"]
            professor = Professor.unfiltered.get(pk=professor_id)
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
            subject_id = request.POST['subject_id']
            merge_subject = Professor.unfiltered.get(pk=subject_id)
            form = ProfessorMergeForm(request, merge_subject, data=request.POST)

            ctx = {}
            ctx.update(csrf(request))
            context = {
                "success": False
            }

            if form.is_valid():
                target_id = form.cleaned_data['target_id']
                merge_target = Professor.unfiltered.get(pk=target_id)

                ProfessorCourse.objects.filter(professor__id=subject_id).update(professor=merge_target)
                Review.unfiltered.filter(professor__id=subject_id).update(professor=merge_target)
                Grade.unfiltered.filter(professor__id=subject_id).update(professor=merge_target)
                context['success'] = True
                context["target_slug"] = merge_target.slug
                merge_subject.delete()

            context['form'] = render_crispy_form(form, form.helper, context=ctx)
            return JsonResponse(context)

        elif action_type is AdminAction.PROFESSOR_DELETE:
            professor_id = int(data["professor_id"])
            professor_type = str(data["professor_type"])
            has_reviews = Review.unfiltered.filter(professor__id=professor_id).exists()
            has_grades = Grade.unfiltered.filter(professor__id=professor_id).exists()
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
                Professor.unfiltered.filter(pk=professor_id).delete()
                response["success_msg"] = "deleted"

            return JsonResponse(response)

        elif action_type is AdminAction.PROFESSOR_SLUG:
            professor_id = int(data["professor_id"])
            professor = Professor.unfiltered.filter(pk=professor_id).first()
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
        review = Review.unfiltered.filter(pk=review_id).first()
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
                ". However, this review is associated with "
                f"an unverified {professor.type}. Please verify {professor.type}"
                f" {professor.name} ({professor.pk}) as soon as possible."
            )

        if reviewer:
            self.email_user(verified_status, professor, reviewer)

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
                split_name = str(professor.name).strip().split(" ")
                first_name = split_name[0].lower().strip()
                last_name = split_name[-1].lower().strip()

                query = Professor.verified.filter(
                    (
                        Q(name__istartswith=first_name) &
                        Q(name__iendswith=last_name)
                    ) |
                    Q(slug="_".join(reversed(split_name)).lower())
                )

                if query.exists():
                    response["error_msg"] = (
                        f"This {professor.type} might be a duplicate of "
                        f"{query[0]}. Please merge or delete this {professor.type}."
                    )

                    return JsonResponse(response)

                if len(split_name) > 2:
                    modal_msg = (
                        f"The name '{professor.name}' is too long and"
                        "can't be slugged automatcially. Please enter a slug below."
                    )

                    # Create the modal form to manualy enter a slug and add it
                    # to the response. The form creates the modal, though it's
                    # actually summoned from admin-action.js
                    ctx = {}
                    ctx.update(csrf(request))
                    form = ProfessorSlugForm(professor, modal_title=modal_msg)
                    response["form"] = render_crispy_form(form, form.helper, context=ctx)
                    response["success_msg"] = modal_msg
                    return JsonResponse(response)

                professor.slug = "_".join(reversed(split_name)).lower()
        else:
            professor.slug = None
            if verified_status is Professor.Status.REJECTED:
                reviews = Review.unfiltered.filter(professor__id=professor.pk)
                reviews.update(status=verified_status)

        professor.status = verified_status
        professor.save()
        response["success_msg"] = "unverified" if verified_status is Professor.Status.PENDING else verified_status.value

        return JsonResponse(response)

    def email_user(self, verified_status: Review.Status, professor: Professor, user: User):
        if not user.send_review_email:
            return

        status_text = 'Under Review' if verified_status is Review.Status.PENDING else verified_status.value.capitalize()
        profile_url = self.request.build_absolute_uri(reverse('profile'))
        professor_url = self.request.build_absolute_uri(professor.get_absolute_url())
        message = (
            f'Your review for <a href="{professor_url}">{professor.name}'
            f"</a> has been {status_text.lower()}.<br />"
            "<br /> If you would no longer like to receive review "
            "verification emails, you can disable them on "
            f'<a href="{profile_url}#settings">'
            "your profile settings page</a>."
        )

        send_email(user, f"PlanetTerp Review {status_text}", message)
