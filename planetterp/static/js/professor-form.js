function submitProfessorForm(form_id, form_type) {
    var url_mappings = {
        "review": "",
        "add": "/add_professor_and_review",
        "edit": "/edit_review"
    }

    $.ajax({
        type: "POST",
        url: url_mappings[form_type],
        data: $(form_id).serialize(),
        success: function(data) {
            if (!(data['success'])) {
                var errors = JSON.parse(data['errors']);
                var field_mapping = {
                    "content":`id_content_${form_type}`,
                    "course":`id_course_${form_type}`,
                    "grade":`id_grade_${form_type}`,
                    "other_course": "id_other_course"
                }

                $(".anonymous-checkbox > div.form-group").addClass("mb-0");

                if (form_type != "review") {
                    delete field_mapping.other_course;
                    field_mapping["name"] = `id_name_${form_type}`;
                }

                if (form_type == "add") {
                    if ("type_" in errors) {
                        $("#div_id_type_").addClass("mb-0");
                        $("#type__errors").html(errors["type_"][0]["message"]);
                        $("#div_id_type_ input[type=radio]").addClass("is-invalid");
                        $("#type__errors").show();
                    } else {
                        $("#div_id_type_").removeClass("mb-0");
                        $("#type__errors").html("");
                        $("#div_id_type_ input[type=radio]").removeClass("is-invalid");
                        $("#type__errors").hide();
                    }
                }

                for ([field_name, html_id] of Object.entries(field_mapping)) {
                    if (field_name in errors) {
                        $(`${form_id} #div_id_${field_name}`).addClass("mb-0");
                        $(`${form_id} #${html_id}`).addClass("is-invalid");
                        $(`${form_id} #${field_name}_errors`).html(errors[field_name][0]["message"]);
                        $(`${form_id} #${field_name}_errors`).show();
                    } else {
                        $(`${form_id} #div_id_${field_name}`).removeClass("mb-0");
                        $(`${form_id} #${html_id}`).removeClass("is-invalid");
                        $(`${form_id} #${field_name}_errors`).html("");
                        $(`${form_id} #${field_name}_errors`).hide();
                    }
                }

                if ("rating" in errors) {
                    $(`${form_id} #rateYo_${form_type}`).rateYo("option", "normalFill", "#dc3545");
                    $(`${form_id} #rating_errors`).html(errors["rating"][0]["message"]);
                    $(`${form_id} #rating_errors`).show();
                } else {
                    $(`${form_id} #rateYo_${form_type}`).rateYo("option", "normalFill", "#808080");
                    $(`${form_id} #rating_errors`).html("");
                    $(`${form_id} #rating_errors`).hide();
                }

            } else {
                var show_banner = (form_type == "edit") ? data["has_changed"] : true;

                if (form_type == "review")
                    $(".anonymous-checkbox > div.form-group").addClass("mb-0");
                else
                    $(`#success-banner-${form_type}`).css({"width": "69rem"});

                $(`${form_id} div.invalid-feedback`).hide();
                $(`${form_id} div.form-group .is-invalid`).removeClass("is-invalid");

                if (show_banner)
                    $(`#success-banner-${form_type}`).removeClass("d-none");

                $(':input', form_id).not(':button, :submit, :reset, :hidden').val('').prop('checked', false);
                $(`#rateYo_${form_type}`).rateYo("option", "rating", 0);

                if (form_type == "add") {
                    $("#id_type__0").val("professor");
                    $("#id_type__1").val("TA");
                }

                if (form_type == "edit") {
                    var review_id = data["id"];
                    var anon_class = Boolean(data["anonymous"]) ? "fa fa-eye-slash" : "fa fa-eye";

                    $(`#review-${review_id} td.review`).html(data["content"]);
                    $(`#rating-${review_id}`).html(rating(Number(data["rating"])));
                    $(`#grade-${review_id}`).html(grade(data["grade"]));
                    $(`#anonymous-${review_id} i`).attr("class", anon_class);

                    if (Boolean(data["unverify"]))
                        $(`#status-${review_id}`).attr("css", {"color": "darkgoldenrod"}).html("Under Review");

                    if (data["course"]) {
                        var el = $(`#course-${review_id}`);
                        el.html(course(data["course"]["name"]));
                        if (el.parent().children().length % 2 != 0)
                            el.after("<br />");
                    }

                    delete data["unverify"];
                    delete data["success"];
                    $(`#update-${review_id}`).attr("onclick", `editReview(${JSON.stringify(data)})`);
                    $("#edit-professor-modal").modal('hide');
                }
            }
        },
        error: function () {
            console.log("HTTP ERROR");
            alert("HTTP ERROR");
        }
    });
}

function rating(rating) {
    var rating_html = '';
    for (let i = 0; i < rating; i++) {
        rating_html += '<i style="margin-top:4px;" class="fas fa-star"></i>\n'
        rating_html += '<i class="far fa-star"></i>\n'
    }

    for (let i = rating; i < 5; i++)
        rating_html += '<i class="far fa-star"></i>\n'

    return rating_html;
}

function grade(grade) {
    var vowel_grades = ["A", "A-", "A+", "F", "XF"];
    var a_str = (vowel_grades.includes(grade)) ? "an" : "a";
    return `Expecting ${a_str} ${grade}`;
 }

 function course(course) {
    return `<a href=/course/${course}>${course}</a>`;
 }
