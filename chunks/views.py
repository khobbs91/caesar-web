from caesar.chunks.models import Chunk, File
from caesar.comments.models import Comment

from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext

import textwrap
import string

def view_chunk(request, chunk_id):
    try:
        chunk = Chunk.objects.get(pk=chunk_id)
        file_data = chunk.file.data
        # Rewind backwards from the offset to the beginning of the line
        first_line_offset = chunk.start
        while file_data[first_line_offset] != '\n':
            first_line_offset -= 1
        first_line_offset += 1

        first_line = file_data.count("\n", 0, first_line_offset)+1

        # TODO: make tab expansion configurable
        # TODO: more robust (custom) dedenting code
        data = file_data[first_line_offset:chunk.end].expandtabs(4)
        lines = enumerate(textwrap.dedent(data).splitlines(), start=first_line)
    except Chunk.DoesNotExist:
        raise Http404
    return render_to_response('chunks/view_chunk.html', { 
        'chunk': chunk,
        'lines': lines
    }, context_instance=RequestContext(request)) 