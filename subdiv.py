import sys
import argparse
import numpy

class Domain(object):
    def __init__(self, mask_path):
        mask = []
        with open(mask_path, 'rU') as f:
            for l in f:
                mask.append(map(int, l.rstrip('\n')))
        self.mask = numpy.array(mask)
        self.wet = numpy.array(self.mask > 0, dtype=int)

    def find_solutions(self, nx, ny):
        solutions = {}
        for ioffset in xrange(1 - nx, 1):
            for joffset in xrange(1 - ny, 1):
                counts = []
                for jstart in xrange(joffset, self.wet.shape[0], ny):
                    current_wet = self.wet[max(0, jstart):jstart + ny, :]
                    for istart in xrange(ioffset, current_wet.shape[1], nx):
                        npoints = current_wet[:, max(0, istart):istart + nx].sum()
                        if npoints > 0:
                            counts.append(npoints)
                solutions.setdefault(len(counts), []).append((ioffset, joffset, counts))
        return solutions

    def plot_solution(self, nx, ny, ioffset, joffset):
        x = numpy.arange(self.mask.shape[1] + 1)
        y = numpy.arange(self.mask.shape[0] + 1)
        pylab.pcolormesh(x, y, self.mask)
        nsubx = int(numpy.ceil((self.mask.shape[1] - ioffset)/float(nx)))
        nsuby = int(numpy.ceil((self.mask.shape[0] - joffset)/float(ny)))
        for istart in range(ioffset, self.mask.shape[1], nx):
            for jstart in range(joffset, self.mask.shape[0], ny):
                pylab.plot((ioffset, ioffset + nsubx*nx), (jstart, jstart), '-k', lw=2)
                pylab.plot((ioffset, ioffset + nsubx*nx), (jstart, jstart), '--w', lw=2)
                pylab.plot((istart, istart), (joffset, joffset + nsuby*ny), '-k', lw=2)
                pylab.plot((istart, istart), (joffset, joffset + nsuby*ny), '--w', lw=2)
                if not self.wet[max(0, jstart):jstart + ny, max(0, istart):istart + nx].any():
                    pylab.plot((istart, istart + nx), (jstart, jstart + ny), '-r', lw=1)
                    pylab.plot((istart, istart + nx), (jstart + ny, jstart), '-r', lw=1)
        pylab.ylim(y[-1], 0)
        pylab.axis('tight')

    def number_subdomains(self, nx, ny, ioffset, joffset):
        nsubx = int(numpy.ceil((self.wet.shape[1] - ioffset)/float(nx)))
        nsuby = int(numpy.ceil((self.wet.shape[0] - joffset)/float(ny)))
        subids = numpy.empty((nsuby, nsubx), dtype=int)
        subids[...] = -1
        n = 0
        for jsub, jstart in enumerate(xrange(joffset, self.wet.shape[0], ny)):
            for isub, istart in enumerate(xrange(ioffset, self.wet.shape[1], nx)):
                if self.wet[max(0, jstart):jstart+ny, max(0, istart):istart+nx].any():
                    subids[jsub, isub] = n
                    n += 1
        return subids

    def save_solution(self, nx, ny, ioffset, joffset, subids, path):
        def getid(i, j):
            outside = i >= subids.shape[1] or i < 0 or j >= subids.shape[0] or j < 0
            return -1 if outside else subids[j, i]
        n = (subids > -1).sum()
        with open(path, 'w') as f:
            f.write('%i\n%i %i %i %i\n' % (n, nx, ny, self.wet.shape[1], self.wet.shape[0]))
            for jstart in range(joffset, self.wet.shape[0], ny):
                for istart in range(ioffset, self.wet.shape[1], nx):
                    isub = (istart - ioffset)/nx
                    jsub = (jstart - joffset)/ny
                    jlast = jstart + ny - 1
                    if subids[jsub, isub] > -1:
                        neighbors = []
                        neighbors.append(getid(isub-1, jsub))
                        neighbors.append(getid(isub-1, jsub-1))
                        neighbors.append(getid(isub,   jsub-1))
                        neighbors.append(getid(isub+1, jsub-1))
                        neighbors.append(getid(isub+1, jsub))
                        neighbors.append(getid(isub+1, jsub+1))
                        neighbors.append(getid(isub,   jsub+1))
                        neighbors.append(getid(isub-1, jsub+1))
                        f.write('%i %i %i %s 1\n' % (subids[jsub, isub], istart, self.wet.shape[0]-jlast, ' '.join(map(str, neighbors))))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mask')
    parser.add_argument('--nx', type=int, default=None)
    parser.add_argument('--ny', type=int, default=None)
    parser.add_argument('--ncpus', type=int, default=None)
    parser.add_argument('--min_nx', type=int, default=None)
    parser.add_argument('--max_nx', type=int, default=None)
    parser.add_argument('--min_ny', type=int, default=None)
    parser.add_argument('--max_ny', type=int, default=None)
    parser.add_argument('--square', action='store_true')
    parser.add_argument('output')
    args = parser.parse_args()

    if args.ncpus is None and args.nx is None and args.ny is None:
        print 'You must provide either --ncpus, or --nx and --ny.'
        sys.exit(2)
    if args.ncpus is None and (args.nx is None or args.ny is None):
        print 'If --ncpus is not provided, both --nx and --ny must be provided instead.'
        sys.exit(2)
    if args.nx is not None and (args.min_nx is not None or args.max_nx is not None):
        print 'If --nx is provided, --min_nx and --max_nx should not be.'
        sys.exit(2)
    if args.ny is not None and (args.min_ny is not None or args.max_ny is not None):
        print 'If --ny is provided, --min_ny and --max_ny should not be.'
        sys.exit(2)
    if args.min_nx is None:
        args.min_nx = 30
    if args.min_ny is None:
        args.min_ny = 30
    if args.max_nx is None:
        args.max_nx = 100
    if args.max_ny is None:
        args.max_ny = 100

    domain = Domain(args.mask)
    if args.ncpus:
        all_solutions = []
        def test(nx, ny):
            print 'Trying nx=%i, ny=%i...' % (nx, ny),
            solutions = domain.find_solutions(nx, ny)
            valid_solutions = solutions.get(args.ncpus, ())
            print '%i valid found' % len(valid_solutions)
            all_solutions.extend([(solution[0], solution[1], solution[2], nx, ny) for solution in valid_solutions])
        if args.nx is not None:
            args.min_nx, args.max_nx = args.nx, args.nx
        if args.ny is not None:
            args.min_ny, args.max_ny = args.ny, args.ny
        for nx in range(args.min_nx, args.max_nx + 1):
            if args.square:
                test(nx, nx)
            else:
                for ny in range(args.min_ny, args.max_ny + 1):
                    test(nx, ny)
        best_solutions = sorted(all_solutions, cmp=lambda x, y: cmp(max(x[2]), max(y[2])))
        ioffset, joffset, counts, nx, ny = best_solutions[0]
        print 'Best solution is has a subdomain size of %i x %i' % (nx, ny)
    else:
        nx, ny = args.nx, args.ny
        solutions = domain.find_solutions(nx, ny)
        minn = min(solutions.keys())
        print 'Minimum number of subdomains: %i' % minn
        best_solutions = sorted(solutions[minn], cmp=lambda x, y: cmp(max(x[2]), max(y[2])))
        ioffset, joffset, counts = best_solutions[0]

    print 'Best solution has a maximum of %i wet points (out of %i) per subdomain' % (max(counts), nx*ny)

    subids = domain.number_subdomains(nx, ny, ioffset, joffset)
    domain.save_solution(nx, ny, ioffset, joffset, subids, args.output)
    print 'Subdomain ids:\n', subids

    import pylab
    domain.plot_solution(nx, ny, ioffset, joffset)
    pylab.show()
