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
    "professor_delete": {
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
    var verified_status = data['verified_status'];
    var unverified_count = Number($("#unverified_count").html());
    $("#unverified_count").html(unverified_count - 1);

    if (verified_status == "unverified") {
        location.reload();
    }

    $("#review-counter").html(args["count"]);

    $(`#review-${data["review_id"]}`).remove();
    //addAdminResponse("#admin-tool-response", successText);
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
        container_id_mappings = {
            "#info-modal-container": "#info-modal",
            "#slug-modal-container": "#slug-modal"
        }

        $(".modal").modal("hide");
        $(data["success_msg"]).html(`${data['form']}`);

        $('#slug-modal').on('show.bs.modal', function (e) {
            $('#override').val("false");
        });

        $(container_id_mappings[data["success_msg"]]).modal('show');
    } else {
        var unverified_count;
        if (data['success_msg'] == "unverified") {
            window.location.href = "/";
        } else {
            var msg = data['success_msg'];

            $("#professor-counter").html(args["count"]);

            if (msg != null) {
                if (msg != "verified") {
                    var professor_reviews = $(`div.unverified_review_${data['id']}`);

                    if (professor_reviews.length > 0) {
                        var num_reviews = Number(args["num_reviews"]) - professor_reviews.length;
                        $("#review-counter").html(num_reviews);
                        professor_reviews.each(function() {
                            $(this).parents("tr").remove();
                        });
                    }
                }
            }

            $(`#professor-${data['id']}`).remove();
            unverified_count = Number($("#unverified_count").html());
            $("#unverified_count").html(unverified_count - 1);
            $("#info-modal").modal('hide');
        }
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
            successText += 'Professor merged successfully!</div>'

        $("#id_merge_subject").removeClass("is-invalid").val("");
        $("#id_merge_target").removeClass("is-invalid").val("");

        location.reload();
    }
}
function mergeProfessorError(data, args) {
    $("#merge-container").html(data["form"]);
    $("#merge-errors").css("display", "flex");
    var csrf_token = $('#merge-form > input[name="csrfmiddlewaretoken"]').val();
    initalizeAutoComplete(csrf_token);
    $('#id_merge_subject').val(data["prof_name"]);
    $('#id_subject_id').val(data["prof_id"]);
    $(".modal-backdrop").remove();
    $("#merge-modal").modal('show');
}

/* ********* SLUG PROFESSOR FUNCTIONS ********* */
function slugProfessorSuccess(data, args) {
    if (!data["success"]) {
        var modal_title = $("#slug-modal-label").html();
        $(".modal-backdrop").remove();
        $("#slug-modal-container").html(`${data['form']}`);
        $("#slug-modal-label").html(modal_title);
        $("#slug_errors").show()
        $("#slug-modal").modal('show');
    } else {
        var successText = "<div class=\"alert alert-success text-center success-alert\">";
            successText += `<strong>Successfully slugged and verified ${data["type"]}.</strong>`
            successText += "</div><br />"

        $("#professor-counter").html(args["count"]);

        $(`#verified_${data['id']}`).parents("tr").remove();
        addAdminResponse("#admin-tool-response", successText);

        $(".modal").modal('hide');
        $("#slug_errors").html();
        $("#slug-form-slug").removeClass("is-invalid");
        $('#slug-modal-container').html();
    }
}
function slugProfessorError(data, args) {
    var parsed_data = JSON.parse(data["error_msg"]);
    var msg = parsed_data['slug'][0]['message'];
    $("#slug_errors").html(msg);
    $("#slug_errors").show();
    $("#slug-form-slug").addClass("is-invalid");
}

/* SHARED FUNCTIONS */
function initalizeAutoComplete(csrf_token) {
    $("#id_merge_target").autocomplete({
        minLength: 3,
        source: function(request, response) {
            $.ajax({
                url: "/autocomplete",
                dataType: 'json',
                data: {
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
}

function mergeProfessor(args) {
    $('#id_merge_subject').val(args["merge_subject"]);
    $('#id_subject_id').val(args["subject_id"]);

    if (args["merge_target"]) {
        $('#id_merge_target').val(args["merge_target"]);
        $('#id_target_id').val(args["target_id"]);
        sendResponse($("#merge-form").serialize(), "professor_merge");
    } else {
        initalizeAutoComplete('{{ csrf_token }}');
        if (location.pathname.includes("professor")) {
            $("#edit-professor-modal").modal('hide');
            $(".modal-backdrop").hide();
        }

        $('#merge-modal').modal('show');
    }
}
