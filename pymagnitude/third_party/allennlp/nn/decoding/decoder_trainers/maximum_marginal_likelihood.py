

from __future__ import division
from __future__ import absolute_import
import logging
#typing

import torch

from allennlp.nn import util
from allennlp.nn.decoding.constrained_beam_search import ConstrainedBeamSearch
from allennlp.nn.decoding.decoder_step import DecoderStep
from allennlp.nn.decoding.decoder_state import DecoderState
from allennlp.nn.decoding.decoder_trainers.decoder_trainer import DecoderTrainer

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class MaximumMarginalLikelihood(DecoderTrainer[Tuple[torch.Tensor, torch.Tensor]]):
    u"""
    This class trains a decoder by maximizing the marginal likelihood of the targets.  That is,
    during training, we are given a `set` of acceptable or possible target sequences, and we
    optimize the `sum` of the probability the model assigns to each item in the set.  This allows
    the model to distribute its probability mass over the set however it chooses, without forcing
    `all` of the given target sequences to have high probability.  This is helpful, for example, if
    you have good reason to expect that the correct target sequence is in the set, but aren't sure
    `which` of the sequences is actually correct.

    This implementation of maximum marginal likelihood requires the model you use to be `locally
    normalized`; that is, at each decoding timestep, we assume that the model creates a normalized
    probability distribution over actions.  This assumption is necessary, because we do no explicit
    normalization in our loss function, we just sum the probabilities assigned to all correct
    target sequences, relying on the local normalization at each time step to push probability mass
    from bad actions to good ones.

    Parameters
    ----------
    beam_size : ``int``, optional (default=None)
        We can optionally run a constrained beam search over the provided targets during decoding.
        This narrows the set of transition sequences that are marginalized over in the loss
        function, keeping only the top ``beam_size`` sequences according to the model.  If this is
        ``None``, we will keep all of the provided sequences in the loss computation.
    """
    def __init__(self, beam_size      = None)        :
        self._beam_size = beam_size

    def decode(self,
               initial_state              ,
               decode_step             ,
               supervision                                   )                           :
        targets, target_mask = supervision

        # If self._beam_size is not set, we use a beam size that ensures we keep all of the
        # sequences.
        beam_size = self._beam_size or targets.size(1)
        beam_search = ConstrainedBeamSearch(beam_size, targets, target_mask)
        finished_states                                = beam_search.search(initial_state, decode_step)

        loss = 0
        for instance_states in list(finished_states.values()):
            scores = [state.score[0].view(-1) for state in instance_states]
            loss += -util.logsumexp(torch.cat(scores))
        return {u'loss': loss / len(finished_states)}
