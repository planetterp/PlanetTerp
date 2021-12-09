const responses = {
    "review_verify": {
        SUCCESS: verifyReviewSuccess,
        ERROR: verifyReviewError
    },
    "review_help": {
        SUCCESS: verifyHelpSuccess
    },
    "professor_verify": {
        SUCCESS: verifyProfessorSuccess,
        ERROR: verifyProfessorError
    },
    "professor_edit": {
        SUCCESS: editProfessorSuccess,
        ERROR: editProfessorError
    },
    "professor_merge": {
        SUCCESS: mergeProfessorSuccess,
        ERROR: mergeProfessorError
    },
    "professor_slug": {
        SUCCESS: slugProfessorSuccess,
        ERROR: slugProfessorError
    }
}

function sendResponse(form_data, tool_type, args = {}) {
    $.ajax({
        type: "POST",
        url: "/admin",
        data: form_data,
        success: function(data) {
            if (data["success"] || data["success_msg"] != null) {
                responses[tool_type].SUCCESS(data, args);
            } else {
                responses[tool_type]?.ERROR(data, args);
            }
        }
    });
}

function addAdminResponse(target, msg) {
    $(target).html(msg);
    $(target).show();

    setTimeout(function() {
        $(target).hide();
    }, 10000);
}

/* ********* VERIFY REVIEW FUNCTIONS ********* */
function verifyReviewSuccess(data, args) {
    var num_reviews = Number(args["count"]);
    var msg = data['success_msg'];
    var verified_status = data['verified_status'];
    var successText = '<div class="alert alert-success text-center success-alert">'
        successText += `<strong>Successfully ${verified_status} review</strong>`

    if (msg != null) {
        successText += msg
    }
    successText += "</div><br />";

    if (verified_status == "unverified") {
        generateProfessorStats(num_reviews);
    }

    $("#review-counter").html(`${num_reviews}`);
    $(`#review-${data["review_id"]}`).remove();
    addAdminResponse("#admin-tool-response", successText);
}
function verifyReviewError(data, args) {
    var errorText = '<div class="alert alert-danger text-center error-alert">'
        errorText += "<strong>Error: </strong>"
        errorText += data['error_msg']
        errorText += "</div><br />";

    addAdminResponse("#admin-tool-response", errorText);
}

/* ********* VERIFY HELP FUNCTIONS ********* */
function verifyHelpSuccess(data, args) {
    var successText = `<div class="alert alert-success text-center success-alert"><strong>${data['response']}</strong></div><br />`;
    addAdminResponse("#admin-tool-response", successText);
}

/* ********* VERIFY PROFESSOR FUNCTIONS ********* */
function verifyProfessorSuccess(data, args) {
    if (data['form'] != null) {
        $("#slug-modal-container").html(`${data['form']}`);
        $(`#slug-modal-${Number(data['id'])}`).modal('show');
    } else {
        if (data['success_msg'] != "unverified") {
            var successText = '<div class="alert alert-success text-center success-alert">'
            var num_professors = Number(args["count"]);
            var id = Number(data['id']);
            var msg = data['success_msg'];

            $("#professor-counter").html(`${num_professors}`);

            if (msg != null) {
                successText += `<strong>Successfully ${msg} ${data["type"]}.`
                if (msg != "verified") {
                    var professor_reviews = $(`div.unverified_review_${id}`);

                    if (professor_reviews.length > 0) {
                        var num_reviews = Number(args["num_reviews"]) - professor_reviews.length;
                        $("#review-counter").html(num_reviews);
                        professor_reviews.each(function() {
                            $(this).parents("tr").remove();
                        });
                        successText += ` Any associated reviews have also been been ${msg}.`
                    }
                }
                successText += "</strong>"
            } else
                successText += `<strong>Successfully slugged and verified ${data["type"]}.</strong>`

            successText += "</div><br />";
            $(`#professor-${id}`).remove();
            addAdminResponse("#admin-tool-response", successText);
        } else
            window.location.href = "/";
    }
}
function verifyProfessorError(data, args) {
    var error_msg = data['error_msg'];

    if (error_msg != null) {
        var errorText = '<div class="alert alert-danger text-center error-alert">'
            errorText += "<strong>Error: </strong> "
            errorText += error_msg
            errorText += "</div><br />";
        addAdminResponse("#admin-tool-response", errorText);
    }
}

/* ********* EDIT PROFESSOR FUNCTIONS ********* */
function editProfessorSuccess(data, args) {
    var name = data['name'];
    if (name != null) {
        var successText = '<div class="alert alert-success text-center success-alert">'
            successText += `<strong>${data["professor_type"]} updated successfully</strong></div><br />`;

        $("#professor-name").html(`<strong>${name}</strong>`);

        ["name", "slug", "type"].forEach(function(key) {
            $(`#edit_${key}`).removeClass(["is-valid", "is-invalid"]);
            $(`#${key}_response`).html("").hide();
        });

        addAdminResponse("#admin-tool-response", successText);
    }

    var slug = data['slug'];
    if (slug != null)
        location.assign(`/professor/${slug}`);
    else {
        var type_ = data['type'];
        if (type_ != null)
            location.reload();
    }

    $("#edit-professor-modal").modal('hide');
    $(".modal-backdrop").remove();
}
function editProfessorError(data, args) {
    var fieldList = ["name", "slug", "type"];
    fieldList.forEach(function(key) {
        if (data[key] == null) {
            $(`#edit_${key}`).removeClass(["is-valid", "is-invalid"]);
            $(`#${key}_response`).html("").hide();
        } else if (data[key] == "valid") {
            $(`#edit_${key}`).removeClass("is-invalid").addClass("is-valid").show();
        } else {
            $(`#edit_${key}`).removeClass("is-valid").addClass("is-invalid").show();
            $(`#${key}_response`).html(data[key]).removeClass("valid-feedback").addClass("invalid-feedback").show();
        }
    });
}

/* ********* MERGE PROFESSOR FUNCTIONS ********* */
function mergeProfessorSuccess(data, args) {
    if (location.pathname.includes("professor")) {
        location.pathname = `/professor/${data["target_slug"]}`;
    } else {
        var successText = '<div class="alert alert-success text-center success-alert">'
            successText += 'Professor merged successfully! </div>'

        $("#id_merge_subject").removeClass("is-invalid").val("");
        $("#id_merge_target").removeClass("is-invalid").val("");

        addAdminResponse("#merge-professor-errors", successText);
    }
}
function mergeProfessorError(data, args) {
    $("#merge-professor-container").html(data["form"]);
    var csrf_token = $('#merge-professor-form > input[name="csrfmiddlewaretoken"]').val();
    if (location.pathname.includes("professor")) {
        $(".modal-backdrop").remove();
        $("#merge-professor-modal").modal('show');
    }
    initalizeAutoComplete(csrf_token);
    $("#merge-professor-errors").show()
}

/* ********* SLUG PROFESSOR FUNCTIONS ********* */
function slugProfessorSuccess(data, args) {
    var id = Number(data['id']);
    if (!data["success"]) {
        var modal_title = $(`#slug-modal-label-${id}`).html();
        $(".modal-backdrop").remove();
        $("#slug-modal-container").html(`${data['form']}`);
        $(`#slug-modal-label-${id}`).html(modal_title);
        $("#slug_errors").show()
        $(`#slug-modal-${id}`).modal('show');
    } else {
        var num_professors = Number(args["count"]);
        var successText = "<div class=\"alert alert-success text-center success-alert\">";
            successText += `<strong>Successfully slugged and verified ${data["type"]}.</strong>`
            successText += "</div><br />"

        $("#professor-counter").html(num_professors);

        $(`#verified_${id}`).parents("tr").remove();
        addAdminResponse("#admin-tool-response", successText);

        $(".modal").modal('hide');
        $(".slug-errors").html();
        $(`#slug-form-slug-${id}`).removeClass("is-invalid");
    }
}
function slugProfessorError(data, args) {
    var id = Number(data['id']);
    var msg = data['error_msg'];
    $(".slug-errors").html(msg);
    $(".slug-errors").show();
    $(`#slug-form-slug-${id}`).addClass("is-invalid");
}

/* SHARED FUNCTIONS */
function swapInputs() {
    var subject = $("#id_merge_subject").val();
    var target = $("#id_merge_target").val();

    var subject_id = $("#id_subject_id").val();
    var target_id = $("#id_target_id").val();

    $("#id_merge_target").val(subject);
    $("#id_merge_subject").val(target);

    $("#id_subject_id").val(target_id);
    $("#id_target_id").val(subject_id);
}

function initalizeAutoComplete(csrf_token) {
    $("#id_merge_target").autocomplete({
        minLength: 3,
        source: function(request, response) {
            $.ajax({
                url: "/autocomplete",
                dataType: 'json',
                data: {
                    'from_professor_page': true,
                    'query': request.term,
                    "types[]": ["professor"],
                    "return_attrs[]": ["pk", "name"],
                    'csrfmiddlewaretoken': csrf_token
                },
                success: function(data) {
                    response(data);
                }
            })
        },
        select: function(event, ui) {
            $("#id_merge_target").val(ui.item.result.name);
            $("#id_target_id").val(ui.item.result.pk);
        }
    });

    $("#id_merge_subject").autocomplete({
        minLength: 3,
        source: function(request, response) {
            $.ajax({
                url: "/autocomplete",
                dataType: 'json',
                data: {
                    'from_professor_page': true,
                    'query': request.term,
                    "types[]": ["professor"],
                    "return_attrs[]": ["pk", "name"],
                    'csrfmiddlewaretoken': csrf_token
                },
                success: function(data) {
                    response(data);
                }
            })
        },
        select: function(event, ui) {
            $("#id_merge_subject").val(ui.item.result.name);
            $("#id_subject_id").val(ui.item.result.pk);
        }
    });
}
