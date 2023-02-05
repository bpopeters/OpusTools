import os
import re
import sys
import html
from itertools import combinations

from .parse.alignment_parser import AlignmentParser
from .parse.sentence_parser import SentenceParser
from .util import file_open
from .formatting import check_lang_conf_type
from .opus_file_handler import OpusFileHandler

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
            languages=None,
            release='latest',
            preprocess='xml',
            maximum=-1,
            attribute=None,
            threshold=None,
            leave_non_alignments_out=False,
            write=None,
            write_mode='normal',
            print_file_names=False,
            root_directory='/projappl/nlpl/data/OPUS',
            alignment_files=tuple(),
            zips=tuple(),
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
        self.verbose = verbose

        self.languages = sorted(languages)
        language_pairs = list(combinations(self.languages, 2))  # tuples

        '''
        self.fromto = [source, target]
        sorted_langs = sorted([source, target])
        assert self.fromto == sorted_langs, \
            "Just stay in alphabetical order for now"
        '''

        lang_filters = [src_cld2, src_langid, trg_cld2, trg_langid]

        # "source" currently means first alphabetically, which is bad(?)
        # source should mean the source, not the first alphabetically
        # do zips
        if not zips:
            zips = []
            for language in languages:
                language_zip = _find_zip(
                    download_dir,
                    directory,
                    root_directory,
                    release,
                    preprocess,
                    language
                )
                zips.append(language_zip)

        self.write_ids = write_ids

        if write is None:
            write = []
        assert len(write) < 2 or write_mode == "moses", \
            "Specifying multiple out files is only allowed in moses mode"

        self.write = write
        self.maximum = maximum
        self.preprocess = 'parsed' if print_annotations else preprocess

        self.preserve = False

        self.annot = source_annotations, target_annotations
        self.annot_delimiter = change_annotation_delimiter

        self._write_mode = write_mode
        self._print_file_names = print_file_names

        self._moses_del = change_moses_delimiter
        self._attribute = attribute

        self.check_filters, check_lang = check_lang_conf_type(lang_filters)

        # I don't like this and I want to get rid of it
        self.of_handler = OpusFileHandler(
            download_dir,
            source_zip,
            target_zip,
            directory,
            release,
            preprocess,
            self.fromto,  # ...
            verbose,
            suppress_prompts
        )

        # opening a file in the constructor for some reason
        if not alignment_files:
            # construct them, one for each pair
            alignment_paths = dict()
            for language_pair in language_pairs:
                align_path = os.path.join(
                    root_directory,
                    directory,
                    release,
                    'xml',
                    "-".join(align_path) + '.xml.gz'
                )
                alignment_paths[language_pair] = align_path
        else:
            assert len(alignment_files) == len(language_pairs)
            alignment_paths = dict(zip(language_pairs, alignment_files))

        # now, make an alignment parser for each pair
        # is this actually the right way to do it?
        # for each align_path, there is a set of links between two languages.
        # You can perhaps build an adjacency graph.
        # keys are (language, id) pairs, values are a set of aligned
        # (language, id) pairs.
        self.alignment_parsers = dict()
        for pair, align_path in alignment_paths.items():
            self.alignment_parsers[pair] = AlignmentParser(
                self.of_handler.open_alignment_file(align_path),
                ("all", "all"),
                attribute,
                threshold,
                leave_non_alignments_out
        )

        self.not_links_or_check_lang = write_mode != "links" or check_lang

    def _output_pair(self, src_result, trg_result, out_paths, link_a):
        if not out_paths:
            outf = sys.stdout
        elif len(out_paths) == 1:
            outf = out_paths[0]
        else:
            assert self._write_mode == "moses"
            outf = out_paths

        moses_del = '\t' if self.write_ids else self._moses_del

        if self._write_mode in {"normal", "tmx"}:
            outf.write(src_result + trg_result)

        elif self._write_mode == "moses":
            if out_paths is not None and len(out_paths) == 2:
                assert len(outf) == 2
                src_outf, trg_outf = outf
                src_outf.write(src_result)
                trg_outf.write(trg_result)
            else:
                # both src_result and trg_result end in \n
                outf.write(src_result[:-1] + moses_del + trg_result)

        elif self._write_mode == "links":
            links = ['{}="{}"'.format(k, v) for k, v in link_a.items()]
            str_link = '<link {} />\n'.format(' '.join(links))
            outf.write(str_link)

    def _write_ids(self, id_file, link_a, src_doc, trg_doc):
        """
        some notes about what to do in the "switch" case (which currently does
        not apply):
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
        """
        ids = link_a['xtargets'].split(';')
        if self._attribute and self._attribute in link_a:
            last_piece = link_a[self._attribute]
        else:
            last_piece = 'None'
        line_pieces = [src_doc, trg_doc, ids[0], ids[1], last_piece]
        id_file.write("\t".join(line_pieces) + "\n")

    def _add_file_header(self, outf):
        if outf is None:
            outf = sys.stdout

        if self._write_mode == "tmx":
            header = ('<?xml version="1.0" encoding="utf-8"?>\n<tmx '
                      'version="1.4.">\n<header srclang="' + self.fromto[0] +
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
        """
        The link pairs the IDs from the src and trg corpora.
        The parsers are glorified dictionaries at this point.
        This method looks up the IDs from the link in the src and trg parsers.
        """
        # why put this check inside the method?
        if not self.not_links_or_check_lang:
            return None, None

        str_src_ids, str_trg_ids = link_a['xtargets'].split(';')
        src_ids = str_src_ids.split()
        trg_ids = str_trg_ids.split()

        src_sentences, src_attrs = src_parser.read_sentence(src_ids)
        trg_sentences, trg_attrs = trg_parser.read_sentence(trg_ids)

        if self.check_filters(src_attrs, trg_attrs):
            return -1, -1

        # it's also weird to put this here
        if self._write_mode == "links":
            return None, None

        if self._switch_langs:
            # adversarial variable naming
            src_result = self._format_sentences(trg_sentences, trg_ids, "src")
            trg_result = self._format_sentences(src_sentences, src_ids, "tgt")
            return src_result, trg_result
        else:
            src_result = self._format_sentences(src_sentences, src_ids, "src")
            trg_result = self._format_sentences(trg_sentences, trg_ids, "trg")
            return src_result, trg_result

    def _format_sentences(self, sentences, ids, side="src"):
        assert side in {"src", "trg"}
        # don't do anything for links
        if self._write_mode == "moses":
            return ' '.join(sentences) + '\n'

        elif self._write_mode == "normal":
            result = '\n================================' if side == "src" else ''
            for i, sentence in enumerate(sentences):
                result += ('\n({})="{}">'.format(side, ids[i]) + sentence)
            return result

        elif self._write_mode == "tmx":
            # need to get fromto...is it still an attribute?
            result = ''
            for sentence in sentences:
                # src case:
                lang = self.fromto[int(side != "src")]
                if side == "src":
                    result += '\t\t<tu>'
                result += ('\n\t\t\t<tuv xml:lang="{}"><seg>'.format(lang))
                result += html.escape(sentence, quote=False) + '</seg></tuv>'
                if side == "trg":
                    result += '\n\t\t</tu>\n'
            return result

        else:
            return None

    def print_pairs(self):

        outfiles = [file_open(path, mode='w', encoding='utf-8')
                    for path in self.write]

        self._add_file_header(outfiles[0] if outfiles else None)

        if self.write_ids:
            id_file = file_open(self.write_ids, 'w', encoding='utf-8')
        else:
            id_file = None  # hmm

        total = 0
        stop = False

        # the think here: we will have several link files, not one
        link_groups = self.alignment_parser.iterate_links()
        for link_group in link_groups:
            # ok, this needs to change
            link_attrs, src_set, trg_set, src_doc_name, trg_doc_name = link_group

            if not src_doc_name:
                break

            # it seems wasteful to load the links before the filter: is there
            # any way to detect the files first?

            parsers = []
            if self.not_links_or_check_lang:
                try:
                    src_doc = self.of_handler.open_sentence_file(src_doc_name, 'src')
                    trg_doc = self.of_handler.open_sentence_file(trg_doc_name, 'trg')
                except KeyError as e:
                    print('\n' + e.args[0] + '\nContinuing from next sentence file pair.')
                    continue

                # for each language, do this
                parser = SentenceParser(
                    src_doc,
                    preprocessing=self.preprocess,
                    anno_attrs=("pos", "lem"),
                    preserve=False
                    delimiter=self.annot_delimiter
                )
                parser.store_sentences(src_set)  # where is the set from?
                trg_parser = SentenceParser(
                    trg_doc,
                    preprocessing=self.preprocess,
                    anno_attrs=trg_annot,
                    preserve=False
                    delimiter=self.annot_delimiter
                )
                trg_parser.store_sentences(trg_set)

            self._add_doc_names(src_doc_name, trg_doc_name, outfiles)

            # write each link
            for link_a in link_attrs:
                # why put this check inside the method?
                src_result, trg_result = self._format_pair(
                    link_a, src_parser, trg_parser
                )
                # what do you do if they're None?

                if src_result == -1:
                    continue

                self._output_pair(src_result, trg_result, outfiles, link_a)
                if self.write_ids:
                    self._write_ids(
                        id_file, link_a, src_doc_name, trg_doc_name
                    )

                total += 1
                if total == self.maximum:
                    stop = True
                    break

            self._add_doc_ending(outfiles[0] if outfiles else None)

            if stop:
                break

        self._add_file_ending(outfiles[0] if outfiles else None)

        if outfiles:
            for outfile in outfiles:
                outfile.close()

        if id_file is not None:
            id_file.close()

        self.of_handler.close_zipfiles()

        if self.verbose:
            print('Done')