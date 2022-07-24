var timeCounter = 0;

$(document).ready(function() {
	$("#schedule-search").autocomplete({
		minLength: 3,
		source: function(request, response) {
			$.ajax({
				url: '/schedule/new',
				type: "POST",
				dataType: 'json',
				data: {
					'query': request.term
				},
				success: function(data) {
					response(data);
				}
			})
		},
		select: function(e, ui) {
			var course = ui.item.label;
			
			createSelectedCourse(course);

			this.value = "";
			e.preventDefault();
		}
	});

	$("#schedule-search").keypress(function (e) { // Allow course search when user
												  // presses enter (rather than clicking
												  // on autocomplete option)

		if (e.which == 13) { // User pressed enter
			var courses = $("#schedule-search").val().toUpperCase().replace(/ /g, '').split(',');

			for (var i = 0; i < courses.length; i++) {
				createSelectedCourse(courses[i]);
			}

			this.value = "";
		}
	});


	$("#select-courses").on('submit', function(e) {
		$('#schedule-search').trigger({type: 'keypress', which: 13, keyCode: 13}); // Add whatever is currently in course search box
		if ($('#start-time-input').val() !== '' || $('#end-time-input').val() !== '') {
			$('#add-time').trigger('click'); // Add whatever time is currently inputted
		}

		var coursesStr = "";

		$('.selected-course').each(function(i, obj) {
			coursesStr += obj.innerText + ",";
		});

		coursesStr = coursesStr.substring(0, coursesStr.length - 1); // Remove end comma

		$("#courses").val(coursesStr);
		$("#restrictions").val($('#no-class').html().replace(/\u2014/g, '-')); // Replace emdash with dash
		$("#max-waitlist").val($('#max-waitlist-input').val());

		// Remove everything except the header and footer
		$('body').children().not('#canvas-wrapper, #page-footer, #loading-message').hide();

		// Show loading icon
		$('#loading-message').show();
	});

	$("#add-time").on('click', function(e) {
		var startTime = $('#start-time-input').val().toUpperCase();
		var endTime = $('#end-time-input').val().toUpperCase();

		if (moment(startTime, 'h:mm a', true).isValid() && moment(endTime, 'h:mm a', true).isValid() && moment(startTime, 'h:mm a', true).isBefore(moment(endTime, 'h:mm a', true))) {
			var days = '';

			if (($('#monday')).is(':checked')) {
				days += 'M';
			}
			if (($('#tuesday')).is(':checked')) {
				days += 'Tu';
			}
			if (($('#wednesday')).is(':checked')) {
				days += 'W';
			}
			if (($('#thursday')).is(':checked')) {
				days += 'Th';
			}
			if (($('#friday')).is(':checked')) {
				days += 'F';
			}

			if (days === '') {
				$('#time-error-text').text("You must select at least one day by clicking on one of the boxes below.")
				$('#time-error').show();
			}
			else {
				createRestriction(days, startTime, endTime);

				$('#monday').prop('checked', false);
				$('#tuesday').prop('checked', false);
				$('#wednesday').prop('checked', false);
				$('#thursday').prop('checked', false);
				$('#friday').prop('checked', false);
				$('#start-time-input').val('');
				$('#end-time-input').val('');

				$('#time-error').hide();
			}
		}
		else if (!moment(startTime, 'h:mm a', true).isValid() || !moment(endTime, 'h:mm a', true).isValid()) {
			$('#time-error-text').text("Invalid time inputted. An example time is '3:30 pm'.")
			$('#time-error').show();
		}
		else if (!(moment(startTime, 'h:mm a', true).isBefore(moment(endTime, 'h:mm a', true)))) {
			$('#time-error-text').text("End time must be after start time.")
			$('#time-error').show();
		}
	});
});

function createSelectedCourse (course) {
	var course_regex = /^((([A-Z]{4}(?:[A-Z]|[0-9]){3,6})(\(([A-Z0-9]{4}\|?)*\))?)|([A-Z]{4}))$/

	if (course_regex.test(course)) {
		if (document.getElementById(course + "-course") === null) {
			var data = "<span id='" + escapeHTML(course).replace("(", "").replace(")", "").replace("|", "") + "-course' class='selected-course'>";
			data += "<span><a href='/course/" + escapeHTML(course).match(/[^\(]*/)[0] + "' target='_blank'>" + escapeHTML(course) + "</a></span>";
			data += "<span class='remove-course'><i class='fas fa-times-circle'></i></span>";
			data += "</span>"
			
			document.getElementById('selected-courses').innerHTML += data;

			$('.fa-times-circle').on('click', function(e) {
				$("#" + e.target.parentElement.parentElement.id).remove();
			});
		}
	}
}

function createRestriction (days, startTime, endTime) {
	$('#no-class').append('<span class="time-wrapper"><span id="time-' + escapeHTML(timeCounter) + '"><br />' + escapeHTML(days) + ' ' + escapeHTML(startTime) + '&mdash;' + escapeHTML(endTime) + '<span class="remove-time"><i class="fas fa-times-circle"></i></span></span></span>');
	timeCounter++;
	$('.fa-times-circle').on('click', function(e) {
		$(e.target.parentElement.parentElement.parentElement).remove();
	});
}

// From: http://shebang.brandonmintern.com/foolproof-html-escaping-in-javascript/
function escapeHTML(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}



