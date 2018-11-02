from copy import deepcopy

class DynamicProgrammingMatrix:
    '''
    Dynamic Programming Matrix that automatically does wrapping modulo N
    '''
    def __init__( self, N, val = 0.0, diag_val = 0.0 ):
        self.N = N
        self.DPmatrix = WrappedArray( N )
        print self.DPmatrix
        for i in range( N ):
            self.DPmatrix[i] = WrappedArray( N )
            print self.DPmatrix
            for j in range( N ):
                self.DPmatrix[i][j] = DynamicProgrammingData( val )
                self.DPmatrix[i][j].info.append( (self,i,j) )

        for i in range( N ): self.DPmatrix[i][i].Q = diag_val

    def __getitem__( self, idx ):
        return self.DPmatrix[ idx ]

    def __len__( self ): return len( self.DPmatrix )

class DynamicProgrammingData:
    '''
    Dynamic programming object, with derivs and contribution accumulation.
     Q   = value
     dQ  = derivative (later will generalize to gradient w.r.t. all parameters)
     contrib = contributions
    '''
    def __init__( self, val = 0.0 ):
        self.Q = val
        self.dQ = 0.0
        self.contrib = []
        self.info = []

    def __iadd__(self, other):
        self.Q += other.Q
        if  len( other.contrib ) > 0: self.contrib += other.contrib
        elif len( other.info ) > 0: self.contrib.append( [other.Q, other.info] )
        return self

    def __mul__(self, other):
        prod = DynamicProgrammingData()
        if isinstance( other, DynamicProgrammingData ):
            prod.Q       = self.Q * other.Q
            info = self.info + other.info
            if len( info ) > 0:
                prod.contrib = [ [ prod.Q, info ] ]
                prod.info = info
        else:
            prod.Q = self.Q * other
            for contrib in self.contrib:
                prod.contrib.append( [contrib[0]*other, contrib[1] ] )
            prod.info = self.info
        return prod

    def __truediv__( self, other ):
        quot = deepcopy( self )
        quot.Q /= other
        return quot

    __rmul__ = __mul__
    __floordiv__ = __truediv__
    __div__ = __truediv__


class WrappedArray:
    '''
    For all the various cross-checks, like equality of partition function starting at any
     i and wrapping around to N and then back 1 and then i-1, need to keep applying modulo N.
    '''
    def __init__( self, N, val = 0.0 ):
        self.array = [val] * N
        self.N = N
    def __getitem__( self, idx ):
        return self.array[idx % self.N]
    def __setitem__( self, idx, item ):
        self.array[idx % self.N] = item
    def __len__( self ):
        return self.N
