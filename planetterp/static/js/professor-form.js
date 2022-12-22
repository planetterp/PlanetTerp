function submitProfessorForm(form_id) {
    if (form_id == '#professor-form-review') {
        rateYo_multiplier = 3.1
        form_type = "review"
        post_url = ""
        container_id = form_id;
    } else {
        rateYo_multiplier = 1.8
        form_type = "add"
        post_url = "/add_professor"
        container_id = "#add-professor-form-container";
    }

    $.ajax({
        type: "POST",
        url: post_url,
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

                if (form_type == "add") {
                    delete field_mapping.other_course;
                    field_mapping["name"] = `id_name_${form_type}`;

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
                if (form_type == "review") {
                    $(".anonymous-checkbox > div.form-group").addClass("mb-0");
                }

                $("div.invalid-feedback").hide();
                $("div.form-group .is-invalid").removeClass("is-invalid");

                $(`#success-banner-${form_type}`).removeClass("d-none");
                $(':input', form_id).not(':button, :submit, :reset, :hidden').val('').prop('checked', false);
                $(`#rateYo_${form_type}`).rateYo("option", "rating", 0);

                if (form_type == "add") {
                    $("#success-banner-add").removeClass("w-100").css({"width": "69rem"});
                    $("#id_type__0").val("professor");
                    $("#id_type__1").val("TA");
                }
            }
        },
        error: function () {
            console.log("HTTP ERROR");
            alert("HTTP ERROR");
        }
    });
}
