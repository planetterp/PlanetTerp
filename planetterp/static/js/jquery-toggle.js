// from https://github.com/apluslms/js-jquery-toggle

(function($) {

	/* A wrapper function to support older versions */
	/* jquery method to make button or button like element a toggle button */
	$.fn.makeToggleButton = function(options) {
		this.makeMultiStateButton({
			num_of_states: 2,
			state: options.active ? 1 : 0,
			multi_icon: false,
			icon_0: options.officon,
			text_0: options.offtext,
			color_0: options.offcolor,
			icon_1: options.onicon,
			text_1: options.ontext,
			color_1: options.oncolor,
			nocolor: options.nocolor,
			clickHandler: options.clickHandler,
		})
	}

	/* A wrapper function to support older versions */
	/* jquery method to replace checkboxes or radio selection with toggle buttons */
	$.fn.replaceCheckboxesWithButtons = function(options) {
		this.replaceInputsWithMultiStateButtons(options)
	}


	/*
	 * Helper function for expressing icons.
	 * Supports Font Awesome (icon names start with 'fa') and
	 * Bootstap glyphicons (provide names without 'glyphicon' -text)
	 * Returns icon-html-element
	 */
	function html_icon(name) {
		if (!name) return ''     // no name, something went wrong
		else if (!name.startsWith('fa') && !name.startsWith('glyphicon')) {
			name = 'glyphicon glyphicon-' + name
		}
		return '<i class="' + name + '"></i>'
	}

	/*Helper function, goes through options and sets min-width to widest*/
	function update_width(html_button) {
		const button = $(html_button)
		const args = button.data('jquery_toggle_options');
		const original_state = args.state;
		const widths = [];
		do {
			widths.push(button.outerWidth());
			button.click();
		} while (args.state != original_state);
		const max_width = Math.max(...widths);
		button.css('min-width', max_width + 'px');
	}

	/*
	 * Helper function to dispatch change event.
	 * jQuery event triggers alert only jQuery event listeners, not native ones.
	 */
	function simulateChange(elem) {
		let event;
		if (typeof Event === 'function') {
			event = new Event('change', {
				bubbles: true,
				cancelable: false,
			});
		} else { // IE11
			event = document.createEvent('Event');
			event.initEvent('change', true, false);
		}
		elem.dispatchEvent(event);
	}


	/*
	 * bound handler for button on:state_change
	 * updates the state of the button element (icons, text and color)
	 */
	function update_mltsb_state(event, state) {
		const button = $(this);
		const args = button.data('jquery_toggle_options');
		const num_of_states = args.num_of_states;
		const prev_state = (state + num_of_states - 1) % num_of_states;
		const act = args[state];
		const prev = args[prev_state];
		// never shrink buttons
		button.css('min-width', button.css('width'));

		args.state = state;
		if (state == 1) button.addClass('active');
		else if (state == 0) button.removeClass('active');
		button.removeClass('mltsb-state-' + prev_state)
			.addClass('mltsb-state-' + state);

		const icon = (
			args.multi_icon ? act.icon.map( function(i) {return html_icon(i)} ).join('')
			: html_icon(act.icon)
		);
		if (!args.nocolor) {
			button.removeClass(prev.color).addClass(act.color);
		}
		button.html(act.text + " " + icon);
	}

	/* bound handler for button on:click and on:toggle_state*/
	function toggle_mltsb_state(event) {
		const button = $(this);
		const args = button.data('jquery_toggle_options');
		const state = (args.state + 1) % args.num_of_states;
		button.triggerHandler('state_change', [state]);
		return state;
	}

	/* bound handler for button on:click when used for select-tags (dropdwns) */
	function select_button_click_handler(event) {
		const button = $(this);
		const input = button.data('input_element');

		const prev = input.children(':selected');
		var active = prev.next();
		if (!active.length) active = input.children(":first");
		active.prop('selected', true);
		active.each(function(i, elem) {
			simulateChange(elem)
		});
		const new_state = input.children().index(active);
		button.triggerHandler('state_change', [new_state]);
	}

	/* bound handler for button on:click when used for checkbox buttons */
	function checkbox_button_click_handler(event) {
		const button = $(this);
		const input = button.data('input_element');

		const active = !input.is(':checked');
		input.prop('checked', active);
		input.each(function (i, elem) {
			simulateChange(elem)
		});
		const state = active ? 1 : 0
		button.triggerHandler('state_change', [state]);
	}

	/* bound handler for button on:click when used for radio buttons */
	function radio_button_click_handler(event) {
		const button = $(this);
		const inputs = button.data('inputs');  // Array[HTMLElement]
		const args = button.data('jquery_toggle_options');
		const prev_state = inputs.findIndex(function (i) {
			return i.checked
		})
		const new_state = (prev_state + 1) % args.num_of_states;
		inputs[new_state].checked = true;
		simulateChange(inputs[new_state]);
		button.triggerHandler('state_change', [new_state]);
	}


	const default_group_options = {
		groupClass: 'btn-group',
	} ;

	const default_multi_state_options = {
		state: 0,
		num_of_states: 2,
		color_0: 'default',
		color: ['primary', 'danger', 'warning', 'success', 'info'],
		nocolor: false,
		clickHandler: toggle_mltsb_state,
		buttonClass: 'btn',
	} ;

	const default_single_icon_options = {
		icon_0: 'unchecked',
		icon_1: 'check',
		icon_2: 'remove',
	} ;

	const bootstrap_multi_icon_options = {
		icon_on: 'ok-sign',
		icon_off: 'record',
	} ;

	const fa_multi_icon_options = {
		icon_on: 'fas fa-circle',
		icon_off: 'far fa-circle',
	} ;


	/* jquery method to make button or button-like element a multi-state-button */
	$.fn.makeMultiStateButton = function(options) {

		const icon_options = (
			(!options.multi_icon) ? default_single_icon_options
			: options.font_awesome ? fa_multi_icon_options
			: bootstrap_multi_icon_options
		)
		const settings = $.extend({}, default_multi_state_options, icon_options, options);

		this.each(function() {
			const button = $(this)
				.addClass(settings.buttonClass)
				.css('text-align', 'center');
			const num_of_states = settings.num_of_states;

			const args = {
				state: settings.state,
				active: settings.state != 0,
				num_of_states: num_of_states,
				nocolor: settings.nocolor,
				multi_icon: settings.multi_icon,
			};
			for (i = 0; i < num_of_states; i++) {
				var icon;
				if (settings.multi_icon) {
					icon = [...Array(num_of_states).keys()].map(function(n) {
						if (n == i) return settings['icon_on_' + n] || settings.icon_on;
						else return settings['icon_off_' + n] || settings.icon_off;
					});
				} else {
					icon = settings['icon_' + i] || ''
				}
				args[i] = {
					icon: icon,
					text: settings['text_' + i] || button.text().trim(),
				};
				if (!settings.nocolor) {
					const color = settings['color_' + i] || settings.color[(i - 1) % settings.color.length];
					args[i]['color'] = 'btn-' + color;
				}
			}
			button.data('jquery_toggle_options', args);

			if (settings.clickHandler !== false) {
				button.on('click', settings.clickHandler);
			}
			button.on('state_change', update_mltsb_state);
			button.on('toggle_state', toggle_mltsb_state);

			// run the handler
			button.triggerHandler('state_change', [args.state]);
		});

		return this;
	};

	/* jquery method to replace checkboxes + radiobuttons or dropdown selections
	 * with multi-state-buttons */
	$.fn.replaceInputsWithMultiStateButtons = function(options) {
		var settings = $.extend({}, default_group_options, options);
		const buttons_by_field = new Map();

		this.each(function() {
			const widget = $(this);
			const radio_buttons = new Map()
			const group = $('<div id="toggle-btn"></div>')
				.addClass(settings.groupClass);
			widget.after(group);

			// goes through group of checkboxes and radio buttons
			if (widget.has('input:checkbox, input:radio').length) {
				widget.find(':input').each(function() {
					input = $(this);

					if (this.type == 'checkbox') {
						const button = $('<button type="button"></button>')
							.addClass(input.data('class'));
						group.append(button);
						args = {
							num_of_states: 2,
							icon_0: this.dataset['offIcon'] || settings.officon || settings.icon_0,
							text_0: this.dataset['offText'] || settings.offtext || settings.text_0 || this.parentNode.innerText.trim(),
							icon_1: this.dataset['onIcon'] || settings.onicon || settings.icon_1,
							text_1: this.dataset['onText'] || settings.ontext || settings.text_1 || this.parentNode.innerText.trim(),
							state: this.checked ? 1 : 0,
							nocolor: settings.nocolor,
							multi_icon: false,
							clickHandler: checkbox_button_click_handler,
							buttonClass: settings.buttonClass,
						};
						if (!settings.nocolor) {
							args['color_0'] = this.dataset['offColor'] || settings.offcolor || settings.color_0;
							args['color_1'] = this.dataset['onColor'] || settings.oncolor || settings.color_1;
						};
						button.makeMultiStateButton(args);
						if (settings.buttonSetup) settings.buttonSetup(input, button);
						button.data('input_element', input);
						input.data('button_element', button);
					}

					else if (this.type == 'radio') {
						const name = this.name;
						var button;
						if (!radio_buttons.has(name)) {
							button = $('<button type="button"></button>')
								.addClass(input.data('class'));
							group.append(button);
							radio_buttons.set(name, button);
							button.data('inputs', [this]);
						} else {
							button = radio_buttons.get(name);
							button.data('inputs').push(this);
						}
						this.dataset['button_element'] = button;
						const multi_icon = (
							this.dataset['type'] == 'multiIcon' ? true
							: this.dataset['type'] == 'singleIcon' ? false
							: undefined
						);
						if (multi_icon) button.data('multiIcon', true);
						else if (multi_icon !== undefined) button.data('multiIcon', false);
					}
					// dropdowns within a group of checkboxes and radio buttons are ignored
				})

				// compiles buttons of all radio options
				radio_buttons.forEach(function(button) {
					const radio_inputs = button.data('inputs');  // Array[HTMLElement]
					const num_of_states = radio_inputs.length;
					var multi_icon = button.data('multiIcon');
					if (multi_icon === undefined) multi_icon = settings.multi_icon;
					if (multi_icon === undefined) multi_icon = num_of_states > 3;
					var selected_state = radio_inputs.findIndex(function(ipt) {return ipt.checked});
					if (selected_state == -1) selected_state = 0  // none were checked
					const args = {
							num_of_states: num_of_states,
							state: selected_state,
							multi_icon: multi_icon,
							nocolor: settings.nocolor,
							clickHandler: radio_button_click_handler,
							buttonClass: settings.buttonClass,
					};
					radio_inputs.forEach(function(input, i) {
						args['text_' + i] = input.dataset['text'] || settings['text_' + i] || input.parentNode.innerText.trim();
						if (multi_icon) {
							args['icon_on_' + i] = input.dataset['iconOn'] || settings['icon_on_' + i];
							args['icon_off_' + i] = input.dataset['iconOff'] || settings['icon_off_' + i];
						} else {
							args['icon_' + i] = input.dataset['icon'] || settings['icon_' + i];
						}
						if (!settings.nocolor) {
							args['color_' + i] = input.dataset['color'] || settings['color_' + i];
						}
					})

					button.makeMultiStateButton(args);
					if (settings.buttonSetup) settings.buttonSetup(input, button);
				})

				//widget.addClass('hidden');
				widget.css("display", "none");

			// group of dropdowns
			} else {
				widget.find("select").each(function() {

					const input = $(this)
					const button = $('<button type="button"></button>')
						.addClass(input.data('class'));
					group.append(button)
					const options = input.children()
					const num_of_states = options.length
					var multi_icon = (
						this.dataset['type'] == 'multiIcon' ? true
						: this.dataset['type'] == 'singleIcon' ? false
						: undefined
					)
					if (multi_icon === undefined) multi_icon = settings.multi_icon;
					if (multi_icon === undefined) multi_icon = num_of_states > 3;
					const icon_off = input.data('iconOff');
					const icon_on = input.data('iconOn');

					const args = {
						num_of_states: num_of_states,
						nocolor: settings.nocolor,
						multi_icon: multi_icon,
						clickHandler: select_button_click_handler,
					}
					const states = options.map(function(i) {
						const elem_value = this.value
						if (multi_icon) {
							args['icon_on_' + i] = this.dataset['iconOn'] || icon_on || settings['icon_on_' + i];
							args['icon_off_' + i] = this.dataset['iconOff'] || icon_off || settings['icon_off_' + i];
						} else {
							args['icon_' + i] = this.dataset['icon'] || settings['icon_' + i];
						}
						args['text_' + i] = this.dataset['text'] || settings['text_' + i] || this.text;
						if (!settings.nocolor) {
							args['color_' + i] = this.dataset['color'] || settings['color_' + i];
						}
						if (this.selected) {
							args.state = i
						}
						return elem_value;
					}).toArray();

					button.makeMultiStateButton(args);
					if (settings.buttonSetup) settings.buttonSetup(input, button);
					button.data('input_element', input);
					input.data('button_element', button);
					//input.parent().addClass('hidden');
					input.parent().css("display", "none");
					update_width(button);
				})
			}

		});

		return this;
	};


}(jQuery));
