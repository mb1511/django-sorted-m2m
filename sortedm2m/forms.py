# -*- coding: utf-8 -*-

from itertools import chain

from django import forms
from django.template.loader import render_to_string
from django.utils.encoding import force_text
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.six import string_types
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType


class SortedCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    class Media:
        js = (
            'admin/js/jquery.init.js',
            'sortedm2m/widget.js',
            'sortedm2m/jquery-ui.js',
        )
        css = {'screen': (
            'sortedm2m/widget.css',
        )}

    def build_attrs(self, attrs=None, **kwargs):
        attrs = dict(attrs or {}, **kwargs)
        attrs = super(SortedCheckboxSelectMultiple, self).build_attrs(attrs)
        classes = attrs.setdefault('class', '').split()
        classes.append('sortedm2m')
        attrs['class'] = ' '.join(classes)
        return attrs

    def render(self, name, value, attrs=None, choices=(), renderer=None):
        if value is None: value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)

        # Normalize to strings
        str_values = [force_text(v) for v in value]

        selected = []
        unselected = []
        model = self.choices.queryset.model()
        content_type = ContentType.objects.get_for_model(model.__class__)

        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = ' for="%s"' % conditional_escape(final_attrs['id'])
            else:
                label_for = ''
                
            url = reverse(
                f"admin:{content_type.app_label}_{content_type.model}_change",
                args=(option_value,),
            )

            cb = forms.CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_text(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(force_text(option_label))
            item = {
                'label_for': label_for,
                'rendered_cb': rendered_cb,
                'option_label': option_label,
                'option_value': option_value,
                'url': url,
            }
            if option_value in str_values:
                selected.append(item)
            else:
                unselected.append(item)

        # re-order `selected` array according str_values which is a set of `option_value`s in the order they should be shown on screen
        ordered = []
        for value in str_values:
            for select in selected:
                if value == select['option_value']:
                    ordered.append(select)
        selected = ordered

        html = render_to_string(
            'sortedm2m/sorted_checkbox_select_multiple_widget.html',
            {'selected': selected, 'unselected': unselected})
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        if isinstance(value, string_types):
            return [v for v in value.split(',') if v]
        return value


class SortedMultipleChoiceField(forms.ModelMultipleChoiceField):
    widget = SortedCheckboxSelectMultiple

    def clean(self, value):
        queryset = super(SortedMultipleChoiceField, self).clean(value)
        if value is None or not hasattr(queryset, '__iter__'):
            return queryset
        key = self.to_field_name or 'pk'
        objects = dict((force_text(getattr(o, key)), o) for o in queryset)
        return [objects[force_text(val)] for val in value]

    def has_changed(self, initial, data):
        if initial is None:
            initial = []
        if data is None:
            data = []
        if len(initial) != len(data):
            return True
        initial_set = [force_text(value) for value in self.prepare_value(initial)]
        data_set = [force_text(value) for value in data]
        return data_set != initial_set
