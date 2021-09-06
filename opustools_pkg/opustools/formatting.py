import html

def write_id_line_type(switch_langs, attribute):
    """Select function for writing id lines"""

    id_temp = '{}\t{}\t{}\t{}\t{}\n'

    def normal(link_a, id_file, src_doc, trg_doc):
        ids = link_a['xtargets'].split(';')
        if attribute in link_a.keys():
            id_file.write(id_temp.format(
                src_doc, trg_doc, ids[0], ids[1], link_a[attribute]))
        else:
            id_file.write(id_temp.format(
                src_doc, trg_doc, ids[0], ids[1], 'None'))

    def normal_no_attr(link_a, id_file, src_doc, trg_doc):
        ids = link_a['xtargets'].split(';')
        id_file.write(id_temp.format(
            src_doc, trg_doc, ids[0], ids[1], 'None'))

    def switch(link_a, id_file, src_doc, trg_doc):
        ids = link_a['xtargets'].split(';')
        if attribute in link_a.keys():
            id_file.write(id_temp.format(
                trg_doc, src_doc, ids[1], ids[0], link_a[attribute]))
        else:
            id_file.write(id_temp.format(
                trg_doc, src_doc, ids[1], ids[0], 'None'))

    def switch_no_attr(link_a, id_file, src_doc, trg_doc):
        ids = link_a['xtargets'].split(';')
        id_file.write(id_temp.format(
            trg_doc, src_doc, ids[1], ids[0], 'None'))

    if switch_langs:
        if attribute:
            return switch
        else:
            return switch_no_attr
    else:
        if attribute:
            return normal
        else:
            return normal_no_attr

def output_type(wmode, write, write_ids, switch_langs, attribute, moses_del):
    """Select function for outputting sentence pairs"""

    #args = (src_result, trg_result, resultfile, mosessrc, mosestrg, link_a,
    #       id_file, src_doc_name, trg_doc_name)
    def normal_write(*args):
        args[2].write(args[0]+args[1])
    def normal_print(*args):
        print(args[0]+args[1], end='')
    def moses_write(*args):
        args[2].write(args[0][:-1]+moses_del+args[1])
    def moses_write_2(*args):
        args[3].write(args[0])
        args[4].write(args[1])
    def moses_print(*args):
        print(args[0][:-1]+moses_del+args[1], end='')
    def links_write(*args):
        str_link = '<link {} />\n'.format(' '.join(
            ['{}="{}"'.format(k, v) for k, v in args[5].items()]))
        args[2].write(str_link)
    def links_print(*args):
        str_link = '<link {} />\n'.format(' '.join(
            ['{}="{}"'.format(k, v) for k, v in args[5].items()]))
        print(str_link, end='')

    write_id_line = write_id_line_type(switch_langs, attribute)

    def normal_write_id(*args):
        args[2].write(args[0]+args[1])
        write_id_line(args[5], args[6], args[7], args[8])
    def normal_print_id(*args):
        print(args[0]+args[1], end='')
        write_id_line(args[5], args[6], args[7], args[8])
    def moses_write_id(*args):
        args[2].write(args[0][:-1]+'\t'+args[1])
        write_id_line(args[5], args[6], args[7], args[8])
    def moses_write_2_id(*args):
        args[3].write(args[0])
        args[4].write(args[1])
        write_id_line(args[5], args[6], args[7], args[8])
    def moses_print_id(*args):
        print(args[0][:-1]+'\t'+args[1], end='')
        write_id_line(args[5], args[6], args[7], args[8])
    def links_write_id(*args):
        str_link = '<link {} />\n'.format(' '.join(
            ['{}="{}"'.format(k, v) for k, v in args[5].items()]))
        args[2].write(str_link)
        write_id_line(args[5], args[6], args[7], args[8])
    def links_print_id(*args):
        str_link = '<link {} />\n'.format(' '.join(
            ['{}="{}"'.format(k, v) for k, v in args[5].items()]))
        print(str_link, end='')
        write_id_line(args[5], args[6], args[7], args[8])

    def nothing(*args):
        pass

    if write_ids:
        if wmode in ['normal', 'tmx'] and write:
            return normal_write_id
        if wmode in ['normal', 'tmx'] and not write:
            return normal_print_id
        if wmode == 'moses' and not write:
            return moses_print_id
        if wmode == 'moses' and len(write) == 1:
            return moses_write_id
        if wmode == 'moses' and len(write) == 2:
            return moses_write_2_id
        if wmode == 'links'and write:
            return links_write_id
        if wmode == 'links'and not write:
            return links_print_id
    else:
        if wmode in ['normal', 'tmx'] and write:
            return normal_write
        if wmode in ['normal', 'tmx'] and not write:
            return normal_print
        if wmode == 'moses' and not write:
            return moses_print
        if wmode == 'moses' and len(write) == 1:
            return moses_write
        if wmode == 'moses' and len(write) == 2:
            return moses_write_2
        if wmode == 'links'and write:
            return links_write
        if wmode == 'links'and not write:
            return links_print
    return nothing


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
