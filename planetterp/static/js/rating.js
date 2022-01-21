// https://rateyo.fundoocode.ninja
function initializeRateYo(multiplier, form_type, show_error_styles) {
	var init_starWidth = ((window.innerWidth * multiplier)/100) + "px";
	var instance_id = "#rateYo_" + form_type
	var rating_field_id = "#id_rating_" + form_type

	$(instance_id).rateYo({
		fullStar: true,
		ratedFill: "gold",
		starWidth: init_starWidth
	});

	if (show_error_styles) {
		$(instance_id).rateYo("option", "normalFill", "#dc3545");
	}

	$(instance_id).on("rateyo.set", function(e, data) {
		var rating = data.rating;
		$(rating_field_id).val(rating);
		$(instance_id).rateYo("option", "normalFill", "#808080");
	});

	if ($(rating_field_id).val() != '') {
		$(instance_id).rateYo("option", "rating", $(rating_field_id).val());
	}
}

function setRateYoSize(wrapper_id, rateYo_instance_id) {
	const NUM_STARS = 5;
	const MIN_STAR_WIDTH = 20;
	var starWidth =  $(wrapper_id).width() / NUM_STARS;
	starWidth = (starWidth >= MIN_STAR_WIDTH ? starWidth : MIN_STAR_WIDTH)
	$(rateYo_instance_id).rateYo("option", "starWidth", starWidth + "px");
}

$(function() {
	$(window).resize(function() {
		setRateYoSize("#review-left-wrapper-add", "#rateYo_add");

		if (window.location.href.includes("/professor/")) {
			setRateYoSize("#review-left-wrapper-review", "#rateYo_review");
		}
	});
});
