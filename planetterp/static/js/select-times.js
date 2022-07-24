$(function() {
	$('#start-time').datetimepicker({
		format: 'LT',
		useCurrent: false
	});
	$('#end-time').datetimepicker({
		format: 'LT'
	});
});