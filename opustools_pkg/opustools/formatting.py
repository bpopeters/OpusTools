import html


def check_lang_confs(lang_filters, attrs):
    names = ('cld2', 'langid')
    for attr in attrs:
        for i, lf in enumerate(lang_filters):
            if lf:
                label = attr[names[i]]
                true_label = lf[0]
                if label != true_label:
                    return False
                score = attr[names[i]+'conf']
                threshold = lf[1]
                if score < threshold:
                    return False
    return True

def check_lang_conf_type(lang_filters):
    def check(src_attrs, trg_attrs):
        return (not check_lang_confs(lang_filters[:2], src_attrs) or
                not check_lang_confs(lang_filters[2:], trg_attrs))
    def no_check(src_attrs, trg_attrs):
        return False

    if any(lang_filters):
        return check, True
    else:
        return no_check, False
