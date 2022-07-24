$(document).ready(function() {
	function sleep(ms) {
		return new Promise(resolve => setTimeout(resolve, ms));
	}


	async function write (values) {
		var search = document.getElementById("schedule-search");

		var last;

		var typed = false;

		while (!typed) {
			shuffle(values);

			// Make sure we don't get the same random value twice in a row
			while (last == values[0]) {
				shuffle(values);
			}

			for (var i = 0; i < values.length; i++) {
				var s = values[i];

				for (var j = 0; j <= s.length; j++) {
					search.placeholder = s.substring(0, j);
					await sleep(50);
				}

				for (var j = 1; j <= 3; j++) {
					search.placeholder += "|";
					await sleep(500);
					search.placeholder = search.placeholder.substring(0, search.placeholder.length - 1);

					if (j != 3) {
						await sleep(500);
					}
					
				}

				for (var j = search.placeholder.length; j >= 0; j--) {
					search.placeholder = search.placeholder.substring(0, j);
					await sleep(50);
				}

				if (search.value != "") {
					search.placeholder = "";
					typed = true;
					break;
				}
			}

			last = s;
		}
	}


	// from https://stackoverflow.com/a/2450976/2150542
	function shuffle(array) {
		var currentIndex = array.length, temporaryValue, randomIndex;

		// While there remain elements to shuffle...
		while (0 !== currentIndex) {
			// Pick a remaining element...
	    	randomIndex = Math.floor(Math.random() * currentIndex);
	    	currentIndex -= 1;

	    	// And swap it with the current element.
	    	temporaryValue = array[currentIndex];
	    	array[currentIndex] = array[randomIndex];
	    	array[randomIndex] = temporaryValue;
		}

		return array;
	}

	var values = ["FSAW", "DSHS, DVUP", "DSSP", "SCIS", "CMSC216, CMSC250", "MUSC490(0201)", "ECON175, ECON111, CHEM131", "JOUR300(0301), DSHU", "ARTT110S", "LARC160(0106|0108), COMM107", "ENGL101(0108|0201|0305)"];

	write(values);
});