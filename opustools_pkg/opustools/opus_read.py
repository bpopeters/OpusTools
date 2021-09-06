import os
import re
import sys

from .parse.alignment_parser import AlignmentParser
from .parse.sentence_parser import SentenceParser, SentenceParserError
from .util import file_open
from .formatting import output_type, sentence_format_type, \
    check_lang_conf_type
from .opus_file_handler import OpusFileHandler


def skip_regex_type(n, N):
    "Select function to skip document names"

    def get_re(doc_name):
        return not re.search(n, doc_name)

    def skip_re(doc_name):
        return re.search(N, doc_name)

    def nothing(doc_name):
        return False

    if n:
        return get_re
    if N:
        return skip_re
    return nothing


def _find_zip(download_dir, directory, root_directory, release, preprocess, language):
    dl_zip = os.path.join(
        download_dir,
        "_".join([directory, release, preprocess, language]) + ".zip"
    )
    if os.path.isfile(dl_zip):
        zip_file = dl_zip
    else:
        zip_file = os.path.join(
            root_directory,
            directory,
            release,
            preprocess,
            language + '.zip'
        )
    return zip_file


class OpusRead:

    def __init__(
            self,
            directory=None,
            source=None,
            target=None,
            release='latest',
            preprocess='xml',
            maximum=-1,
            src_range='all',
            tgt_range='all',
            attribute=None,
            threshold=None,
            leave_non_alignments_out=False,
            write=None,
            write_mode='normal',
            print_file_names=False,
            root_directory='/projappl/nlpl/data/OPUS',
            alignment_file=-1,
            source_zip=None,
            target_zip=None,
            change_moses_delimiter='\t',
            print_annotations=False,
            source_annotations=('pos', 'lem'),
            target_annotations=('pos', 'lem'),
            change_annotation_delimiter='|',
            src_cld2=None,
            trg_cld2=None,
            src_langid=None,
            trg_langid=None,
            write_ids=None,
            suppress_prompts=False,
            download_dir='.',
            preserve_inline_tags=False,
            n=None,
            N=None,
            verbose=False):
        """Read xces alignment files and xml sentence files and output in
        desired format.

        Arguments:
        directory -- Corpus directory name
        source -- Source language
        target -- Target language
        release -- Corpus release version (default latest)
        preprocess -- Corpus preprocessing type (default xml)
        maximum -- Maximum number of alignments outputted (default all)
        src_range -- Number of source sentences in alignment (default all)
        tgt_range -- Number of target sentences in alignment (default all)
        attribute -- Set attribute for filtering
        threshold -- Set threshold for filtering attribute
        leave_non_alignment_out -- Leave non-alignments out
        write -- Write to a given file name. Give two file names to write
            moses format to two files.
        write_mode -- Set write mode (default normal)
        print_file_names -- Print file names when using moses format
        root_directory -- Set root directory for corpora
            (default /projappl/nlpl/data/OPUS)
        alignment_file -- Use given alignment file
        source_zip -- Use given source zip file
        target_zip -- Use given target zip file
        change_moses_delimiter -- Change moses delimiter (default tab)
        print_annotations -- Print annotations if they exist
        source_annotations -- Set source annotations to be printed
            (default pos,lem)
        target_annotations -- Set target annotations to be printed
            (default pos,lem)
        change_annotation_delimiter -- Change annotation delimiter (default |)
        src_cld2 -- Filter source sentence by cld2 language ids and confidence
        trg_cld2 -- Filter target sentence by cld2 language ids and confidence
        src_langid -- Filter source sentence by langid.py language ids and
            confidence
        trg_langid -- Filter target sentence by langid.py language ids and
            confidence
        write_ids -- Write sentence ids to a given file
        suppress_prompts -- Download necessary files without prompting "(y/n)"
        download_dir -- Directory where files will be downloaded (default .)
        preserve_inline_tags -- Preserve inline tags within sentences
        n -- Get only documents that match the regex
        N -- Skip all doucments that match the regex
        verbose -- Print progress messages
        """
        self.source = source  # might not be same as fromto[0]
        fromto = sorted([source, target])
        self.fromto = fromto
        switch_langs = fromto != [source, target]

        self.verbose = verbose

        if switch_langs:
            src_range, tgt_range = tgt_range, src_range
            src_cld2, trg_cld2 = trg_cld2, src_cld2
            src_langid, trg_langid = trg_langid, src_langid
            source_zip, target_zip = target_zip, source_zip
            # still thinking what to do with the last one:
            temp = source_annotations.copy()
            source_annotations = target_annotations.copy()
            target_annotations = temp.copy()

        lang_filters = [src_cld2, src_langid, trg_cld2, trg_langid]

        if alignment_file == -1:
            alignment = os.path.join(
                root_directory,
                directory,
                release,
                'xml',
                "-".join(fromto) + '.xml.gz'
            )
        else:
            alignment = alignment_file

        if not source_zip:
            source_zip = _find_zip(
                download_dir,
                directory,
                root_directory,
                release,
                preprocess,
                fromto[0]
            )
        if not target_zip:
            target_zip = _find_zip(
                download_dir,
                directory,
                root_directory,
                release,
                preprocess,
                fromto[1]
            )

        self.write_ids = write_ids

        if write is None:
            write = []
        assert len(write) < 2 or write_mode == "moses", \
            "Specifying multiple out files is only allowed in moses mode"

        self.write = write
        self.maximum = maximum
        self.preprocess = 'parsed' if print_annotations else preprocess

        self.preserve = preserve_inline_tags

        self.annot = source_annotations, target_annotations
        self.annot_delimiter = change_annotation_delimiter

        self.skip_doc = skip_regex_type(n, N)

        self._write_mode = write_mode
        self._print_file_names = print_file_names

        # args = (src_result, trg_result, resultfile, mosessrc, mosestrg,
        # link_a, id_file, src_doc_name, trg_doc_name)
        self.output_pair = output_type(
            write_mode,  # attribute
            write,  # attribute
            write_ids,  # attribute
            switch_langs,
            attribute,
            change_moses_delimiter
        )

        form_sent_langs = fromto.copy()
        if switch_langs:
            form_sent_langs = fromto[::-1]
        self._switch_langs = switch_langs

        self.format_sentences = sentence_format_type(write_mode, form_sent_langs)

        self.check_filters, check_lang = check_lang_conf_type(lang_filters)

        self.of_handler = OpusFileHandler(
            download_dir,
            source_zip,
            target_zip,
            directory,
            release,
            preprocess,
            fromto,
            verbose,
            suppress_prompts
        )

        alignment = self.of_handler.open_alignment_file(alignment)
        self.alignment_parser = AlignmentParser(
            alignment,
            (src_range, tgt_range),
            attribute,
            threshold,
            leave_non_alignments_out
        )

        self.not_links_or_check_lang = write_mode != "links" or check_lang

    def _add_file_header(self, outf):
        if outf is None:
            outf = sys.stdout

        if self._write_mode == "tmx":
            header = ('<?xml version="1.0" encoding="utf-8"?>\n<tmx '
                      'version="1.4.">\n<header srclang="' + self.source +
                      '"\n\tadminlang="en"\n\tsegtype="sentence"\n\tdatatype='
                      '"PlainText" />\n\t<body>\n')
            outf.write(header)
        elif self._write_mode == "links":
            header = ('<?xml version="1.0" encoding="utf-8"?>\n'
                      '<!DOCTYPE cesAlign PUBLIC "-//CES//DTD XML cesAlign//EN" "">\n'
                      '<cesAlign version="1.0">\n')
            outf.write(header)

    def _add_doc_names(self, src_doc_name, trg_doc_name, out_paths):
        if not out_paths:
            outf = sys.stdout
        elif len(out_paths) == 1:
            outf = out_paths[0]
        else:
            assert self._write_mode == "moses"
            outf = out_paths

        if self._write_mode == "normal":
            template = '\n# {}\n# {}\n'
            outf.write(template.format(src_doc_name, trg_doc_name))

        elif self._write_mode == "links":
            template = ' <linkGrp targType="s" fromDoc="{}" toDoc="{}">\n'
            outf.write(template.format(src_doc_name, trg_doc_name))

        elif self._write_mode == "moses":
            if out_paths is not None and len(out_paths) == 2:
                assert len(outf) == 2
                # the order of labels seems to be backwards if the src language
                # is not alphabetically before the trg
                src_outf, trg_outf = outf
                src_outf.write('\n<fromDoc>{}</fromDoc>\n\n'.format(src_doc_name))
                trg_outf.write('\n<toDoc>{}</toDoc>\n\n'.format(trg_doc_name))
            else:
                template = '\n<fromDoc>{}</fromDoc>\n<toDoc>{}</toDoc>\n\n'
                outf.write(template.format(src_doc_name, trg_doc_name))

    def _add_doc_ending(self, outf):
        if not outf:
            outf = sys.stdout

        # either write or print, you know the drill
        if self._write_mode == "normal":
            outf.write('\n================================\n')
        elif self._write_mode == "links":
            outf.write(' </linkGrp>\n')

    def _add_file_ending(self, outf):
        if not outf:
            outf = sys.stdout
        if self._write_mode == "tmx":
            outf.write('\t</body>\n</tmx>\n')
        elif self._write_mode == "links":
            outf.write('</cesAlign>\n')

    def _format_pair(self, link_a, src_parser, trg_parser):
        if not self.not_links_or_check_lang:
            return None, None

        str_src_ids, str_trg_ids = link_a['xtargets'].split(';')
        src_ids = str_src_ids.split()
        trg_ids = str_trg_ids.split()

        src_sentences, src_attrs = src_parser.read_sentence(src_ids)
        trg_sentences, trg_attrs = trg_parser.read_sentence(trg_ids)

        if self.check_filters(src_attrs, trg_attrs):
            return -1, -1

        if self._write_mode == "links":
            return None, None

        if self._switch_langs:
            # adversarial variable naming
            src_result = self.format_sentences[0](trg_sentences, trg_ids)
            trg_result = self.format_sentences[1](src_sentences, src_ids)
            return src_result, trg_result
        else:
            src_result = self.format_sentences[0](src_sentences, src_ids)
            trg_result = self.format_sentences[1](trg_sentences, trg_ids)
            return src_result, trg_result

    def print_pairs(self):

        outfiles = [file_open(path, mode='w', encoding='utf-8')
                    for path in self.write]

        self._add_file_header(outfiles[0] if outfiles else None)

        if outfiles:
            assert len(outfiles) <= 2
            if len(outfiles) == 2:
                resultfile, mosessrc, mosestrg = None, *outfiles
            else:
                resultfile, mosessrc, mosestrg = outfiles[0], None, None
        else:
            resultfile, mosessrc, mosestrg = None, None, None

        if self.write_ids:
            id_file = file_open(self.write_ids, 'w', encoding='utf-8')

        src_parser = None
        trg_parser = None

        total = 0
        stop = False

        while True:
            link_attrs, src_set, trg_set, src_doc_name, trg_doc_name = \
                self.alignment_parser.collect_links()

            if not src_doc_name:
                break

            if self.skip_doc(src_doc_name):
                continue

            if self.not_links_or_check_lang:
                try:
                    src_doc = self.of_handler.open_sentence_file(src_doc_name, 'src')
                    trg_doc = self.of_handler.open_sentence_file(trg_doc_name, 'trg')
                except KeyError as e:
                    print('\n' + e.args[0] + '\nContinuing from next sentence file pair.')
                    continue

                try:
                    src_annot, trg_annot = self.annot
                    src_parser = SentenceParser(
                        src_doc,
                        preprocessing=self.preprocess,
                        anno_attrs=src_annot,
                        preserve=self.preserve,
                        delimiter=self.annot_delimiter
                    )
                    src_parser.store_sentences(src_set)
                    trg_parser = SentenceParser(
                        trg_doc,
                        preprocessing=self.preprocess,
                        anno_attrs=trg_annot,
                        preserve=self.preserve,
                        delimiter=self.annot_delimiter
                    )
                    trg_parser.store_sentences(trg_set)
                except SentenceParserError as e:
                    print('\n' + e.message + '\nContinuing from next sentence file pair.')
                    continue

            self._add_doc_names(src_doc_name, trg_doc_name, outfiles)

            for link_a in link_attrs:
                src_result, trg_result = self._format_pair(
                    link_a, src_parser, trg_parser
                )

                if src_result == -1:
                    continue

                self.output_pair(
                    src_result,
                    trg_result,
                    resultfile,
                    mosessrc,
                    mosestrg,
                    link_a,
                    id_file,
                    src_doc_name,
                    trg_doc_name
                )

                total += 1
                if total == self.maximum:
                    stop = True
                    break

            self._add_doc_ending(outfiles[0] if outfiles else None)

            if stop:
                break

        self._add_file_ending(outfiles[0] if outfiles else None)

        self.alignment_parser.bp.close_document()

        if outfiles:
            for outfile in outfiles:
                outfile.close()

        if id_file is not None:
            id_file.close()

        self.of_handler.close_zipfiles()

        if self.verbose:
            print('Done')
