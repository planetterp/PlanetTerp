from typing import Optional
import json

from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.template.context_processors import csrf
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse
from django.utils.safestring import mark_safe

from crispy_forms.utils import render_crispy_form
from discord_webhook import DiscordWebhook, DiscordEmbed

from home.models import Review, Professor, ProfessorAlias, ProfessorCourse, Grade, User
from home.utils import AdminAction
from home.tables.reviews_table import UnverifiedReviewsTable
from home.tables.basic import ProfessorsTable
from home.forms.admin_forms import (ProfessorMergeForm, ProfessorSlugForm,
    ProfessorUpdateForm, ActionForm, ProfessorInfoModal)
from home.utils import send_email, _ttl_cache, create_autoslug
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
        merge_professor_form = ProfessorMergeForm(request)
        action_form = ActionForm()

        ttl_cache_items = []
        for key, item in _ttl_cache.items():
            # [key, time_salt, value]
            val = [key, item[0], item[1]]
            ttl_cache_items.append(val)

        context = {
            "reviews": reviews,
            "professors": professors,
            "reviews_table": reviews_table,
            "professors_table": professors_table,
            "action_form": action_form,
            "merge_professor_form": merge_professor_form,
            "ttl_cache_items": ttl_cache_items
        }

        context.update(csrf(request))

        return render(request, "admin.html", context)

    def post(self, request):
        data = request.POST
        action_type = AdminAction(data["action_type"])
        user = request.user

        if action_type is AdminAction.REVIEW_VERIFY:
            verified_status = Review.Status(data["verified"])
            review_id = int(data["id_"])
            return self.verify_review(review_id, verified_status, user)

        if action_type is AdminAction.REVIEW_HELP:
            channel_url = config.WEBHOOK_URL_HELP
            review = Review.unfiltered.select_related().get(pk=int(data["id_"]))
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
                username = "Anonymous" if (review.anonymous or not review.user) else review.user.username

                embed.add_embed_field(name="Reviewer", value=username, inline=True)
                embed.add_embed_field(name="Rating", value=review.rating, inline=True)
                embed.add_embed_field(name="Course", value=course, inline=True)
                embed.add_embed_field(name="Grade", value=grade, inline=True)
                embed.add_embed_field(name="Review", value=review_text, inline=False)

                webhook.add_embed(embed)
                webhook.execute()
            return JsonResponse({"response": "Help request sent", "success": True})

        elif action_type is AdminAction.PROFESSOR_VERIFY:
            verified_status = Professor.Status(data["verified"])
            professor_id = int(data["id_"])
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
            professors = Professor.unfiltered.exclude(status=Professor.Status.REJECTED)
            merge_subject = professors.get(pk=subject_id)
            form = ProfessorMergeForm(request, data=request.POST)

            ctx = {}
            ctx.update(csrf(request))
            context = {
                "success": False
            }

            if form.is_valid():
                target_id = form.cleaned_data['target_id']
                merge_target = professors.get(pk=target_id)
                professor_courses = ProfessorCourse.objects.all()
                reviews = Review.unfiltered.all()
                grades = Grade.unfiltered.all()
                professor_aliases = ProfessorAlias.objects.all()

                professor_courses.filter(professor__id=subject_id).update(professor=merge_target)
                reviews.filter(professor__id=subject_id).update(professor=merge_target)
                grades.filter(professor__id=subject_id).update(professor=merge_target)
                professor_aliases.filter(professor=merge_subject).update(professor=merge_target)

                aliases = professor_aliases.filter(alias=merge_subject.name)
                if not (aliases.exists() or professors.filter(name=merge_subject.name).count() > 1):
                    ProfessorAlias(alias=merge_subject.name, professor=merge_target).save()

                context['success'] = True
                context["target_slug"] = merge_target.slug
                merge_subject.delete()

            context["prof_name"] = merge_subject.name
            context["prof_id"] = merge_subject.pk
            context['form'] = render_crispy_form(form, form.helper, context=ctx)
            return JsonResponse(context)

        elif action_type is AdminAction.PROFESSOR_DELETE:
            professor_id = int(data["id_"])
            professor_type = Professor.unfiltered.get(pk=professor_id).type
            has_reviews = Review.verified.filter(professor__id=professor_id).exists()
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
                lst_str = professor_data[0]

                if len(professor_data) == 2:
                    lst_str = f"{professor_data[0]} and {professor_data[1]}"
                elif len(professor_data) == 3:
                    professor_data[-1] = "and " + professor_data[-1]
                    lst_str = ', '.join(professor_data)

                response["error_msg"] = (
                    f"This {professor_type} still has {lst_str} data and cannot be "
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

            if not form.is_valid():
                context["error_msg"] = form.errors.as_json()
                return JsonResponse(context)

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
                ctx = {}
                ctx.update(csrf(request))

                similar_professors = Professor.find_similar(professor.name, 70)
                verify_override = json.loads(request.POST["override"])

                if not verify_override and len(similar_professors) > 0:
                    form = ProfessorInfoModal(professor, similar_professors)
                    response["form"] = render_crispy_form(form, form.helper, context=ctx)
                    response["success_msg"] = "#info-modal-container"
                    return JsonResponse(response)

                new_slug = create_autoslug(professor.name)
                modal_msg = None

                if new_slug is None:
                    modal_msg = (
                        f"The name '{professor.name}' cannot be slugged "
                          "automatically. Please enter a slug below."
                        )

                if modal_msg:
                    # Create the modal form to manualy enter a slug and add it
                    # to the response. The form creates the modal, though it's
                    # actually summoned from admin-action.js
                    form = ProfessorSlugForm(professor, modal_title=modal_msg)
                    response["form"] = render_crispy_form(form, form.helper, context=ctx)
                    response["success_msg"] = "#slug-modal-container"
                    return JsonResponse(response)

                professor.slug = new_slug
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

        status_map = {
            Review.Status.PENDING: "Unverified",
            Review.Status.REJECTED: "Rejected",
            Review.Status.VERIFIED: "Verified"
        }
        status_text = status_map[verified_status]

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
