$(document).ready(function() {
	var currentSchedule = 1;

	var loading = false;

	// Only one schedule:
	if (!(document.getElementById('schedule-' + (currentSchedule + 1)))) {
		$('#next-schedule-right').hide();
	}

	var registerCourses = $('#register-link-schedule-' + currentSchedule)[0].innerHTML.replace(/[^0-9A-Z_/|]/g, '');;
	$('#register-link').attr('href', 'https://app.testudo.umd.edu/testudo/main/dropAdd?venusTermId=202101&crslist=' + registerCourses);

	var sections = $('#schedule-' + currentSchedule + '-ids')[0].innerHTML.replace(/[^0-9,]/g, '');
	$('#share-link').html('https://planetterp.com/schedule?sections=' + sections);

	$('#prev-schedule').on('click', function(e) {
		if (currentSchedule > 1) {
			$('#schedule-' + currentSchedule).hide();
			currentSchedule--;
			$('#schedule-' + currentSchedule).show();
			$('#schedule-information-button').attr('data-target', '#schedule-information-' + currentSchedule);

			$('#schedule-number').text(currentSchedule);

			var registerCourses = $('#register-link-schedule-' + currentSchedule)[0].innerHTML.replace(/[^0-9A-Z_/|]/g, '');;
			$('#register-link').attr('href', 'https://app.testudo.umd.edu/testudo/main/dropAdd?venusTermId=202101&crslist=' + registerCourses);

			var sections = $('#schedule-' + currentSchedule + '-ids')[0].innerHTML.replace(/[^0-9,]/g, '');
			$('#share-link').html('https://planetterp.com/schedule?sections=' + sections);
		}

		$('#next-schedule-right').show();

		if (currentSchedule == 1) {
			$('#next-schedule-left').hide();
		}
	});

	$('#next-schedule').on('click', function(e) {
		$('#next-schedule-left').show();

		if (currentSchedule % 10 !== 0 || (document.getElementById('schedule-' + (currentSchedule + 1)))) {
			$('#schedule-' + currentSchedule).hide();
			currentSchedule++;
			$('#schedule-' + currentSchedule).show();
			$('#schedule-information-button').attr('data-target', '#schedule-information-' + currentSchedule);

			$('#schedule-number').text(currentSchedule);

			var registerCourses = $('#register-link-schedule-' + currentSchedule)[0].innerHTML.replace(/[^0-9A-Z_/|]/g, '');;
			$('#register-link').attr('href', 'https://app.testudo.umd.edu/testudo/main/dropAdd?venusTermId=202101&crslist=' + registerCourses);

			var sections = $('#schedule-' + currentSchedule + '-ids')[0].innerHTML.replace(/[^0-9,]/g, '');
			$('#share-link').html('https://planetterp.com/schedule?sections=' + sections);
			
			if (!(document.getElementById('schedule-' + (currentSchedule + 1))) && (currentSchedule % 10 !== 0)) {
				$('#next-schedule-right').hide();
			}
		}
		else if (!loading) {
			loading = true;
			$('#loading-icon').show();
			$.ajax({
				type: "POST",
				data: {
					'load_more': 'true'
				},
				success: function(data) {
					if (data == "") {
						$('#next-schedule-right').hide();
					}
					else {
						$('#schedules').append(data);
						loading = false;

						$('#schedule-' + currentSchedule).hide();
						currentSchedule++;

						$('#schedule-' + currentSchedule).show();
						$('#schedule-information-button').attr('data-target', '#schedule-information-' + currentSchedule);
						$('#schedule-number').text(currentSchedule);

						var registerCourses = $('#register-link-schedule-' + currentSchedule)[0].innerHTML.replace(/[^0-9A-Z_/|]/g, '');;
						$('#register-link').attr('href', 'https://app.testudo.umd.edu/testudo/main/dropAdd?venusTermId=202101&crslist=' + registerCourses);

						var sections = $('#schedule-' + currentSchedule + '-ids')[0].innerHTML.replace(/[^0-9,]/g, '');
						$('#share-link').html('https://planetterp.com/schedule?sections=' + sections);

						if (!(document.getElementById('schedule-' + (currentSchedule + 1)))) {
							$('#next-schedule-right').hide();
						}
					}

					$('#loading-icon').hide();
				}
			});
		}
	});

	$("#save-form").on('submit', function(e) {
		saveSchedule(currentSchedule);
	});
});
