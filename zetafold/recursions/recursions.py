##################################################################################################
# recursions.py          = user-editable, easier to read (but slower in Python) recursions. Edit this one!
#                           can force zetafold.py to use it with --simple.
#
# explicit_recursions.py = generated by create_explicit_recursions.py from recursions.py. This
#                           is the one used by default in zetafold.py due to speed.
##################################################################################################
def update_Z_cut( self, i, j ):
    '''
    Z_cut is the partition function for independently combining one contiguous/bonded segment emerging out of i to a cutpoint c, and another segment that goes from c+1 to j.
    Useful for Z_BP and Z_final calcs below.
    Analogous to 'exterior' Z in Mathews calc & Dirks multistrand calc.
    '''
    (C_init, l, l_BP,  K_coax, l_coax, C_std, min_loop_length, allow_strained_3WJ, N, \
     sequence, ligated, all_ligated, Z_BP, C_eff_basic, C_eff_no_BP_singlet, C_eff_no_coax_singlet, C_eff, Z_linear, Z_cut, Z_coax ) = unpack_variables( self )
    offset = ( j - i ) % N
    for c in range( i, i+offset ):
        if not ligated[c]:
            # strand 1  (i --> c), strand 2  (c+1 -- > j)
            if c == i and (c+1)%N == j:                                 Z_cut[i][j].Q += 1.0
            if c == i and (c+1)%N != j and ligated[j-1]:                Z_cut[i][j] += Z_linear[c+1][j-1]
            if c != i and (c+1)%N == j and ligated[i]:                  Z_cut[i][j] += Z_linear[i+1][c]
            if c != i and (c+1)%N != j and ligated[i] and ligated[j-1]: Z_cut[i][j] += Z_linear[i+1][c] * Z_linear[c+1][j-1]

##################################################################################################
def update_Z_BPq( self, i, j, base_pair_type ):
    '''
    Z_BPq is the partition function for all structures that base pair i and j with base_pair_type
    Relies on previous Z contributions available for subfragments, and Z_cut for this fragment i,j
    '''

    (C_init, l, l_BP,  K_coax, l_coax, C_std, min_loop_length, allow_strained_3WJ, N, \
     sequence, ligated, all_ligated, Z_BP, C_eff_basic, C_eff_no_BP_singlet, C_eff_no_coax_singlet, C_eff, Z_linear, Z_cut, Z_coax ) = unpack_variables( self )
    offset = ( j - i ) % N

    ( C_eff_for_coax, C_eff_for_BP ) = (C_eff, C_eff ) if allow_strained_3WJ else (C_eff_no_BP_singlet, C_eff_no_coax_singlet )

    (Z_BPq, Kdq)  = ( self.Z_BPq[ base_pair_type ], base_pair_type.Kd )

    if ligated[i] and ligated[j-1]:
        # base pair closes a loop
        #
        #    ~~~~~~
        #   ~      ~
        # i+1      j-1
        #   \       /
        #    i ... j
        #
        Z_BPq[i][j]  += (1.0/Kdq ) * ( C_eff_for_BP[i+1][j-1] * l * l * l_BP)

        # base pair forms a stacked pair with previous pair
        #
        #  i+1 ... j-1
        #    |     |
        #    i ... j
        #
        # Note that base pair stacks (C_eff_stack) could also be handled by this MotifType object, but
        #      it turns out that the get_match_base_pair_type_sets() function below is just too damn slow.
        for base_pair_type2 in self.possible_base_pair_types[i+1][j-1]:
            Z_BPq2 = self.Z_BPq[base_pair_type2]
            Z_BPq[i][j]  += (1.0/Kdq ) * self.params.C_eff_stack[base_pair_type][base_pair_type2] * Z_BPq2[i+1][j-1]

    possible_motif_types = self.possible_motif_types[i][j]
    for motif_type in possible_motif_types[base_pair_type]:
        match_base_pair_type_sets = motif_type.get_match_base_pair_type_sets( sequence, all_ligated, i, j )
        if match_base_pair_type_sets:
            if len(match_base_pair_type_sets) == 1: # hairpins (1-way junctions)
                # base pair closes a hairpin
                #            -----
                #           |     |
                #           i ... j
                #          5' bpt  3'
                #
                Z_BPq[i][j].Q += (1.0/Kdq ) * motif_type.C_eff
                pass
            elif len(match_base_pair_type_sets) == 2: # internal loops (2-way junctions)
                # base pair forms a motif with previous pair
                #
                # Example of 1x1 loop:
                #             bpt0
                #       i_next... j_next
                #           |     |
                #  strand0 i+1   j-1 strand1
                #           |     |
                #           i ... j
                #          5' bpt1 3'
                #
                for (base_pair_type_next, i_next, j_next) in match_base_pair_type_sets[0]:
                    Z_BPq_next = self.Z_BPq[base_pair_type_next]
                    Z_BPq[i][j] += (1.0/Kdq ) * motif_type.C_eff * Z_BPq_next[i_next][j_next]
            # could certainly handle 3WJ in O(N^3) time as well
            # but how about 4WJ? anyway to do without an O(N^4) cost?

    # base pair brings together two strands that were previously disconnected
    #
    #   \       /
    #    i ... j
    #
    Z_BPq[i][j] += (C_std/Kdq) * Z_cut[i][j]

    if K_coax > 0.0:
        if ligated[i] and ligated[j-1]:

            # coaxial stack of bp (i,j) and (i+1,k)...  "left stack",  and closes loop on right.
            #      ___
            #     /   \
            #  i+1 ... k - k+1 ~
            #    |              ~
            #    i ... j - j-1 ~
            #
            for k in range( i+2, i+offset-1 ):
                if ligated[k]: Z_BPq[i][j] += Z_BP[i+1][k] * C_eff_for_coax[k+1][j-1] * l**2 * l_coax * K_coax / Kdq

            # coaxial stack of bp (i,j) and (k,j-1)...  close loop on left, and "right stack"
            #            ___
            #           /   \
            #  ~ k-1 - k ... j-1
            # ~              |
            #  ~ i+1 - i ... j
            #
            for k in range( i+2, i+offset-1 ):
                if ligated[k-1]: Z_BPq[i][j] += C_eff_for_coax[i+1][k-1] * Z_BP[k][j-1] * l**2 * l_coax * K_coax / Kdq

        # "left stack" but no loop closed on right (free strands hanging off j end)
        #      ___
        #     /   \
        #  i+1 ... k -
        #    |
        #    i ... j -
        #
        if ligated[i]:
            for k in range( i+2, i+offset ):
                Z_BPq[i][j] += Z_BP[i+1][k] * Z_cut[k][j] * C_std * K_coax / Kdq

        # "right stack" but no loop closed on left (free strands hanging off i end)
        #       ___
        #      /   \
        #   - k ... j-1
        #           |
        #   - i ... j
        #
        if ligated[j-1]:
            for k in range( i, i+offset-1 ):
                Z_BPq[i][j] += Z_cut[i][k] * Z_BP[k][j-1] * C_std * K_coax / Kdq

    # key 'special sauce' for derivative w.r.t. Kd
    if self.options.calc_deriv_DP: Z_BPq[i][j].dQ += -(1.0/Kdq) * Z_BPq[i][j].Q

##################################################################################################
def update_Z_BP( self, i, j ):
    '''
    Z_BP is the partition function for all structures that base pair i and j.
    All the Z_BPq (partition functions for each base pair type) must have been
    filled in already for i,j.
    '''
    (C_init, l, l_BP,  K_coax, l_coax, C_std, min_loop_length, allow_strained_3WJ, N, \
     sequence, ligated, all_ligated, Z_BP, C_eff_basic, C_eff_no_BP_singlet, C_eff_no_coax_singlet, C_eff, Z_linear, Z_cut, Z_coax ) = unpack_variables( self )

    for base_pair_type in self.possible_base_pair_types[i][j]:
        Z_BPq = self.Z_BPq[base_pair_type]
        Z_BPq.update( self, i, j )
        Z_BP[i][j]  += Z_BPq[i][j]

##################################################################################################
def update_Z_coax( self, i, j ):
    '''
    Z_coax(i,j) is the partition function for all structures that form coaxial stacks between (i,k) and (k+1,j) for some k
    '''
    (C_init, l, l_BP,  K_coax, l_coax, C_std, min_loop_length, allow_strained_3WJ, N, \
     sequence, ligated, all_ligated, Z_BP, C_eff_basic, C_eff_no_BP_singlet, C_eff_no_coax_singlet, C_eff, Z_linear, Z_cut, Z_coax ) = unpack_variables( self )
    offset = ( j - i ) % N

    if (offset == N-1) and ligated[j]: return

    #  all structures that form coaxial stacks between (i,k) and (k+1,j) for some k
    #
    #       -- k - k+1 -
    #      /   :    :   \
    #      \   :    :   /
    #       -- i    j --
    #
    if K_coax > 0:
        for k in range( i+1, i+offset-1 ):
            if ligated[k]:
                if Z_BP.val(i,k) == 0.0: continue
                if Z_BP.val(k+1,j) == 0.0: continue
                Z_coax[i][j]  += Z_BP[i][k] * Z_BP[k+1][j] * K_coax

##################################################################################################
def update_C_eff_basic( self, i, j ):
    '''
    C_eff tracks the effective molarity of a loop starting at i and ending at j
    Assumes a model where each additional element multiplicatively reduces the effective molarity, by
      the variables l, l_BP,  K_coax, etc.
    Relies on previous Z_BP, C_eff_basic, C_eff_no_BP_singlet, C_eff_no_coax_singlet, C_eff, Z_linear available for subfragments.
    Relies on Z_BP being already filled out for i,j
    TODO: In near future, will include possibility of multiple C_eff terms, which combined together will
      allow for free energy costs of loop closure to scale approximately log-linearly rather than
      linearly with loop size.
    '''
    offset = ( j - i ) % self.N

    (C_init, l, l_BP,  K_coax, l_coax, C_std, min_loop_length, allow_strained_3WJ, N, \
     sequence, ligated, all_ligated, Z_BP, C_eff_basic, C_eff_no_BP_singlet, C_eff_no_coax_singlet, C_eff, Z_linear, Z_cut, Z_coax ) = unpack_variables( self )


    # j is not base paired or coaxially stacked: Extension by one residue from j-1 to j.
    #
    #    i ~~~~~~ j-1 - j
    #
    allow_loop_extension = not ( self.in_forced_base_pair and self.in_forced_base_pair[j] )
    if ligated[j-1] and allow_loop_extension: C_eff_basic[i][j] += C_eff[i][j-1] * l

    exclude_strained_3WJ = (not allow_strained_3WJ) and (offset == N-1) and ligated[j]

    # j is base paired, and its partner is k > i. (look below for case with i and j base paired)
    #                 ___
    #                /   \
    #    i ~~~~k-1 - k...j
    #
    C_eff_for_BP = C_eff_no_coax_singlet if exclude_strained_3WJ else C_eff
    for k in range( i+1, i+offset):
        if ligated[k-1]: C_eff_basic[i][j] += C_eff_for_BP[i][k-1] * l * Z_BP[k][j] * l_BP

    if K_coax > 0:
        # j is coax-stacked, and its partner is k > i.  (look below for case with i and j coaxially stacked)
        #               _______
        #              / :   : \
        #              \ :   : /
        #    i ~~~~k-1 - k   j
        #
        C_eff_for_coax = C_eff_no_BP_singlet if exclude_strained_3WJ else C_eff
        for k in range( i+1, i+offset):
            if ligated[k-1]: C_eff_basic[i][j] += C_eff_for_coax[i][k-1] * Z_coax[k][j] * l * l_coax

##################################################################################################
def update_C_eff_no_coax_singlet( self, i, j ):
    (C_init, l, l_BP,  K_coax, l_coax, C_std, min_loop_length, allow_strained_3WJ, N, \
     sequence, ligated, all_ligated, Z_BP, C_eff_basic, C_eff_no_BP_singlet, C_eff_no_coax_singlet, C_eff, Z_linear, Z_cut, Z_coax ) = unpack_variables( self )

    # some helper arrays that prevent closure of any 3WJ with a single coaxial stack and single helix with not intervening loop nucleotides
    C_eff_no_coax_singlet[i][j] += C_eff_basic[i][j]
    C_eff_no_coax_singlet[i][j] += C_init * Z_BP[i][j] * l_BP

##################################################################################################
def update_C_eff_no_BP_singlet( self, i, j ):
    (C_init, l, l_BP,  K_coax, l_coax, C_std, min_loop_length, allow_strained_3WJ, N, \
     sequence, ligated, all_ligated, Z_BP, C_eff_basic, C_eff_no_BP_singlet, C_eff_no_coax_singlet, C_eff, Z_linear, Z_cut, Z_coax ) = unpack_variables( self )

    if K_coax > 0.0:
        C_eff_no_BP_singlet[i][j] += C_eff_basic[i][j]
        C_eff_no_BP_singlet[i][j] += C_init * Z_coax[i][j] * l_coax

##################################################################################################
def update_C_eff( self, i, j ):
    (C_init, l, l_BP,  K_coax, l_coax, C_std, min_loop_length, allow_strained_3WJ, N, \
     sequence, ligated, all_ligated, Z_BP, C_eff_basic, C_eff_no_BP_singlet, C_eff_no_coax_singlet, C_eff, Z_linear, Z_cut, Z_coax ) = unpack_variables( self )

    C_eff[i][j] += C_eff_basic[i][j]

    # j is base paired, and its partner is i
    #      ___
    #     /   \
    #  i+1 ... j-1
    #    |     |
    #    i ... j
    #
    C_eff[i][j] += C_init * Z_BP[i][j] * l_BP

    if K_coax > 0.0:
        # j is coax-stacked, and its partner is i.
        #       ------------
        #      /   :    :   \
        #      \   :    :   /
        #       -- i    j --
        #
        C_eff[i][j] += C_init * Z_coax[i][j] * l_coax

##################################################################################################
def update_Z_linear( self, i, j ):
    '''
    Z_linear tracks the total partition function from i to j, assuming all intervening residues are covalently connected (or base-paired).
    Relies on previous Z_BP, C_eff_basic, C_eff_no_BP_singlet, C_eff_no_coax_singlet, C_eff, Z_linear available for subfragments.
    Relies on Z_BP being already filled out for i,j
    '''
    offset = ( j - i ) % self.N

    (C_init, l, l_BP,  K_coax, l_coax, C_std, min_loop_length, allow_strained_3WJ, N, \
     sequence, ligated, all_ligated, Z_BP, C_eff_basic, C_eff_no_BP_singlet, C_eff_no_coax_singlet, C_eff, Z_linear, Z_cut, Z_coax ) = unpack_variables( self )

    # j is not base paired: Extension by one residue from j-1 to j.
    #
    #    i ~~~~~~ j-1 - j
    #
    allow_loop_extension = ( not self.in_forced_base_pair ) or ( not self.in_forced_base_pair[j] )
    if ligated[j-1] and allow_loop_extension: Z_linear[i][j] += Z_linear[i][j-1]

    # j is base paired, and its partner is i
    #     ___
    #    /   \
    #    i...j
    #
    Z_linear[i][j] += Z_BP[i][j]

    # j is base paired, and its partner is k > i
    #                 ___
    #                /   \
    #    i ~~~~k-1 - k...j
    #
    for k in range( i+1, i+offset):
        if ligated[k-1]: Z_linear[i][j] += Z_linear[i][k-1] * Z_BP[k][j]

    if K_coax > 0.0:
        # j is coax-stacked, and its partner is i.
        #       ------------
        #      /   :    :   \
        #      \   :    :   /
        #       -- i    j --
        #
        Z_linear[i][j] += Z_coax[i][j]

        # j is coax-stacked, and its partner is k > i.
        #
        #               _______
        #              / :   : \
        #              \ :   : /
        #    i ~~~~k-1 - k   j
        #
        for k in range( i+1, i+offset):
            if ligated[k-1]: Z_linear[i][j] += Z_linear[i][k-1] * Z_coax[k][j]


##################################################################################################
def update_Z_final( self, i ):
    # Z_final is total partition function, and is computed at end of filling dynamic programming arrays
    # Get the answer (in N ways!) --> so final output is actually Z_final(i), an array.
    # Equality of the array is tested in run_cross_checks()
    (C_init, l, l_BP, K_coax, l_coax, C_std, min_loop_length, allow_strained_3WJ, N, \
     sequence, ligated, all_ligated, Z_BP, C_eff_basic, C_eff_no_BP_singlet, C_eff_no_coax_singlet, C_eff, Z_linear, Z_cut, Z_coax ) = unpack_variables( self )

    Z_final = self.Z_final
    if not ligated[(i - 1)]:
        #
        #      i ------- i-1
        #
        #     or equivalently
        #        ________
        #       /        \
        #       \        /
        #        i-1    i
        #
        Z_final[i] += Z_linear[i][i-1]
    else:
        # Need to 'ligate' across i-1 to i
        # Scaling Z_final by Kd_lig/C_std to match previous literature conventions

        # Need to remove Z_coax contribution from C_eff, since its covered by C_eff_stacked_pair below.
        Z_final[i] += C_eff_no_coax_singlet[i][i-1] * l / C_std

        #any split segments, combined independently
        #
        #   c+1 --- i-1 - i --- c
        #               *
        for c in range( i, i + N - 1):
            if not ligated[c]: Z_final[i] += Z_linear[i][c] * Z_linear[c+1][i-1]

        for j in range( i+1, (i + N - 1) ):
            # base pair forms a stacked pair with previous pair
            #
            #              <--3'
            #         - j+1 - j -
            #  bpt2 |    :    :    ^ bpt1
            #       V    :    :    |
            #         - i-1 - i -
            #               * 5'-->
            #
            if ligated[j]:
                if Z_BP.val(i,j) > 0.0 and Z_BP.val(j+1,i-1) > 0.0:
                    for base_pair_type in self.params.base_pair_types:
                        if self.Z_BPq[base_pair_type].val(i,j) == 0.0: continue
                        for base_pair_type2 in self.params.base_pair_types:
                            if self.Z_BPq[base_pair_type2].val(j+1,i-1) == 0.0: continue
                            Z_BPq1 = self.Z_BPq[base_pair_type]
                            Z_BPq2 = self.Z_BPq[base_pair_type2]
                            # could also use self.params.C_eff_stack[base_pair_type.flipped][base_pair_type2]  -- should be the same as below.
                            Z_final[i] += self.params.C_eff_stack[base_pair_type2.flipped][base_pair_type] * Z_BPq2[j+1][i-1] * Z_BPq1[i][j]

            # ligation allows an internal loop motif to form across i-1 to i
            #
            #           <--
            #        - j_next ----------- j -
            # bpt0 |      :                 :   ^ bpt1
            #      v      :                 :   |
            #        - k_next - i-1 - i - k -
            #                       *  -->
            #
            #   where k = i, i+1, ... (i + strand_length-2),
            #      i.e., ligation is inside last strand of motif
            #
            for motif_type in self.params.motif_types:
                if len( motif_type.strands) != 2: continue
                for k in range( i, i+len( motif_type.strands[-1] )-1 ):
                    match_base_pair_type_sets = motif_type.get_match_base_pair_type_sets( sequence, all_ligated, j, k )
                    if match_base_pair_type_sets == None: continue
                    assert( len(match_base_pair_type_sets) == 2 )
                    (match_base_pair_type_sets0, match_base_pair_type_sets1) = match_base_pair_type_sets
                    for (base_pair_type1,k_match,j_match) in match_base_pair_type_sets1:
                        assert( (j - j_match)%N == 0 )
                        assert( (k - k_match)%N == 0 )
                        for (base_pair_type0,j_next,k_next) in match_base_pair_type_sets0:
                            Z_BPq0 = self.Z_BPq[base_pair_type0]
                            Z_BPq1 = self.Z_BPq[base_pair_type1]
                            Z_final[i]  += motif_type.C_eff * Z_BPq0[j_next][k_next] * Z_BPq1[k][j]


        # ligation allows an internal loop motif to form across i-1 to i
        #
        #        <--3'
        #       ------- j -
        #      |        :  ^ bpt1
        #      |        :  |
        #     i-1 - i - k -
        #         * 5'-->
        #   where k = i, i+1, ... (i + strand_length-2),
        #      i.e., ligation is inside hairpin loop
        for motif_type in self.params.motif_types:
            if len( motif_type.strands) != 1: continue
            L = len( motif_type.strands[0] ) # for a tetraloop this is 1+4+1 = 6
            for k in range( i, i+L-1 ):
                j = ( k - L + 1 ) % N
                match_base_pair_type_sets = motif_type.get_match_base_pair_type_sets( sequence, all_ligated, j, k )
                if match_base_pair_type_sets == None: continue
                assert( len(match_base_pair_type_sets) == 1 )
                for (base_pair_type,k_match,j_match) in match_base_pair_type_sets[0]:
                    assert( (j - j_match)%N == 0 )
                    assert( (k - k_match)%N == 0 )
                    Z_BPq1 = self.Z_BPq[base_pair_type]
                    Z_final[i]  += motif_type.C_eff * Z_BPq1[k][j]


        if K_coax > 0:
            C_eff_for_coax = C_eff if allow_strained_3WJ else C_eff_no_BP_singlet

            # New co-axial stack might form across ligation junction
            for j in range( i + 1, i + N - 2):
                # If the two coaxially stacked base pairs are connected by a loop.
                #
                #       ~~~~
                #   -- k    j --
                #  /   :    :   \
                #  \   :    :   /
                #   - i-1 - i --
                #         *
                for k in range( j + 2, i + N - 1):
                    if not ligated[j]: continue
                    if not ligated[k-1]: continue
                    if Z_BP.val(i,j) == 0: continue
                    if Z_BP.val(k,i-1) == 0: continue
                    Z_final[i] += Z_BP[i][j] * C_eff_for_coax[j+1][k-1] * Z_BP[k][i-1] * l * l * l_coax * K_coax

                # If the two stacked base pairs are in split segments
                #
                #      \    /
                #   -- k    j --
                #  /   :    :   \
                #  \   :    :   /
                #   - i-1 - i --
                #         *
                for k in range( j + 1, i + N - 1):
                    if Z_BP.val(i,j) == 0: continue
                    if Z_BP.val(k,i-1) == 0: continue
                    if (k-j)%N == 1 and ligated[j]: continue
                    Z_final[i] += Z_BP[i][j] * Z_cut[j][k] * Z_BP[k][i-1] * K_coax


##################################################################################################
def unpack_variables( self ):
    '''
    This helper function just lets me write out equations without
    using "self" which obscures connection to my handwritten equations
    In C++, will just use convention of object variables like N_, sequence_.
    '''
    return self.params.get_variables() + \
           ( self.N, self.sequence, self.ligated, self.all_ligated,  \
             self.Z_BP,self.C_eff_basic,self.C_eff_no_BP_singlet,self.C_eff_no_coax_singlet,self.C_eff,\
             self.Z_linear,self.Z_cut,self.Z_coax )

