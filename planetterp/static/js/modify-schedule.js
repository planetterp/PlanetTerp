function saveSchedule(scheduleId) {
	var sections = $('#schedule-' + scheduleId + '-ids')[0].innerHTML.replace(/[^0-9,]/g, '');
	$('#sections-save').val(sections);
}