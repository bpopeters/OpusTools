from .block_parser import BlockParser, BlockParserError

class AlignmentParserError(Exception):

    def __init__(self, message):
        """Raise error when alignment parsing fails.

        Arguments:
        message -- Error message to be printed
        """
        self.message = message

def range_filter_type(src_range, trg_range):
    def range_filter(*args):
        """Flag if number of ids is outside given ranges"""

        #args = (s_id, t_id, link_attr)
        if src_range != 'all':
            # this seems completely broken to me
            if len(args[0]) not in src_range:
                return True
        if trg_range != 'all':
            if len(args[1]) not in trg_range:
                return True
        return False
    return range_filter

def attribute_filter_type(attribute, threshold):
    def attribute_filter(*args):
        """Flag if attribute score doesn't cross threshold"""

        #args = (s_id, t_id, link_attr)
        if attribute not in args[2].keys():
            #if attribute is not included in link_attr, should this return True or False?
            return True
        if float(args[2][attribute]) < threshold:
            return True
        return False
    return attribute_filter

def non_alignment_filter(*args):
    """Flag if there are no source or target ids"""

    #args = (s_id, t_id, link_attr)
    if len(args[0]) == 0 or len(args[1]) == 0:
        return True
    return False


def _build_filters(src_trg_range, attr, thres, leave_non_alignments_out):
    filters = []
    if src_trg_range != ('all', 'all'):
        src_range, trg_range = src_trg_range
        nums = src_range.split('-')
        if nums[0].isnumeric():
            src_range = set(range(int(nums[0]), int(nums[-1]) + 1))
        nums = trg_range.split('-')
        if nums[0].isnumeric():
            trg_range = set(range(int(nums[0]), int(nums[-1]) + 1))
        filters.append(range_filter_type(src_range, trg_range))

    if attr and thres:
        filters.append(attribute_filter_type(attr, float(thres)))

    if leave_non_alignments_out:
        filters.append(non_alignment_filter)

    return filters


class AlignmentParser:

    def __init__(self, alignment_file, src_trg_range=('all', 'all'),
                 attr=None, thres=None, leave_non_alignments_out=False):
        """Parse xces alignment files and output sentence ids."""

        self.bp = BlockParser(alignment_file)
        self.filters = _build_filters(
            src_trg_range, attr, thres, leave_non_alignments_out
        )

    def filter_link(self, link):
        attr = link.attributes
        src_id, trg_id = attr['xtargets'].split(';')
        return any(filt(src_id.split(), trg_id.split(), attr) for filt in self.filters)

    def collect_links(self):
        """Collect links for a linkGrp"""

        attrs = []
        src_id_set, trg_id_set = set(), set()
        src_doc, trg_doc = None, None

        try:
            blocks = self.bp.get_complete_blocks()
            while blocks:
                for block in blocks:
                    if block.name == 'link':
                        if not self.filter_link(block):
                            src_id, trg_id = block.attributes['xtargets'].split(";")
                            src_id_set.update(src_id.split())
                            trg_id_set.update(trg_id.split())
                            attrs.append(block.attributes)
                    elif block.name == 'linkGrp':
                        src_doc = block.attributes['fromDoc']
                        trg_doc = block.attributes['toDoc']
                        return attrs, src_id_set, trg_id_set, src_doc, trg_doc
                blocks = self.bp.get_complete_blocks()
        except BlockParserError as error:
            raise AlignmentParserError(
                'Error while parsing alignment file: {error}'.format(error=error.args[0]))

        return attrs, src_id_set, trg_id_set, src_doc, trg_doc
