import openvoronoi as ovd # https://github.com/aewallin/openvoronoi
import ovdvtk             # for VTK visualization, https://github.com/aewallin/openvoronoi
import ttt   			  # https://github.com/aewallin/truetype-tracer

import offset2vtk         # vtk visualization helper https://github.com/aewallin/openvoronoi

import time
import vtk
import math

# insert points into diagram, return list of point IDs
def insert_polygon_points(vd, polygon):
    pts=[]
    for p in polygon:
        pts.append( ovd.Point( p[0], p[1] ) )
    id_list = []
    print "inserting ",len(pts)," point-sites:"
    m=0
    for p in pts:
        id_list.append( vd.addVertexSite( p ) )
        print " ",m," added vertex ", id_list[ len(id_list) -1 ]
        m=m+1    
    return id_list

# insert polygon line-segments based on a list of IDs
# [0, 1, 2, 3, 4, 5] defines a closed polygon
# 0->1->2->3->4->5->0 
def insert_polygon_segments(vd,id_list):
    j=0
    print "inserting ",len(id_list)," line-segments:"
    for n in range(len(id_list)):
        n_nxt = n+1
        if n==(len(id_list)-1):
            n_nxt=0
        print " ",j,"inserting segement ",id_list[n]," - ",id_list[n_nxt]
        vd.addLineSite( id_list[n], id_list[n_nxt])
        j=j+1

# insert many polygons into vd
# segs is a list of polygons
# segs = [poly1, poly2, poly3, ...]
# poly defines a closed polygon as a a list of points
# [ [x1,y1], [x2,y2], [x3,y3], ... ]
# where the last point in the list connects to the first
def insert_many_polygons(vd,segs):
    polygon_ids =[]
    t_before = time.time()
    # all points must be inserted into the vd first!
    for poly in segs:
        poly_id = insert_polygon_points(vd,poly)
        polygon_ids.append(poly_id)
    t_after = time.time()
    pt_time = t_after-t_before
    
    # all line-segments are inserted then
    t_before = time.time()
    for ids in polygon_ids:
        insert_polygon_segments(vd,ids)
    
    t_after = time.time()
    seg_time = t_after-t_before
    
    return [pt_time, seg_time]

# translate all segments by x,y
def translate(segs,x,y):
    out = []
    for seg in segs:
        seg2 = []
        for p in seg:
            p2 = []
            p2.append(p[0] + x)
            p2.append(p[1] + y)
            seg2.append(p2)
        out.append(seg2)
    return out

# call truetype-tracer to get font input geometry
# text is the text-string we want
# scale is used to scale the geometry to fit within a unit-circle
def ttt_segments(text,scale):
    wr = ttt.SEG_Writer()
    wr.arc = False
    wr.conic = False
    wr.cubic = False

    wr.conic_biarc_subdivision = 10 # this has no effect?
    wr.conic_line_subdivision = 50 # this increases nr of points 
    wr.cubic_biarc_subdivision = 10 # no effect?
    wr.cubic_line_subdivision = 10 # no effect?
    wr.setFont(3)
    
    wr.scale = float(1)/float(scale)
    ttt.ttt(text,wr) 
    segs = wr.get_segments()
    return segs

# the segments come out of truetype-tracer in a slightly wrong format
# truetype-tracer outputs closed polygons with identical points
# at the start and end of the point-list. here we get rid of this repetition.
def modify_segments(segs):
    segs_mod =[]
    for seg in segs:
        first = seg[0]
        last = seg[ len(seg)-1 ]
        assert( first[0]==last[0] and first[1]==last[1] )
        seg.pop()
        seg.reverse() # to get interior or exterior offsets
        segs_mod.append(seg)
        #drawSegment(myscreen, seg)
    return segs_mod

if __name__ == "__main__":  
    #w=2500
    #h=1500
    
    w=1920 # width and height of VTK viewport
    h=1080
    #w=1024
    #h=1024
    myscreen = ovdvtk.VTKScreen(width=w, height=h) 
    ovdvtk.drawOCLtext(myscreen, rev_text=ovd.version() )   
    
    scale=1
    myscreen.render()

    far = 1
    camPos = far
    zmult = 3
    # camPos/float(1000)
    myscreen.camera.SetPosition(0, -camPos/float(1000), zmult*camPos) 
    myscreen.camera.SetClippingRange(-(zmult+1)*camPos,(zmult+1)*camPos)
    myscreen.camera.SetFocalPoint(0.0, 0, 0)
    
    # use far==1 for now. This means all input geometry should fit within a unit circle!
    # 120 is a binning-parameter for nearest neighbor search. sqrt(n) where we have n points should be ok (?)
    vd = ovd.VoronoiDiagram(far,120)
    print ovd.version()
    
    # for vtk visualization
    vod = ovdvtk.VD(myscreen,vd,float(scale), textscale=0.01, vertexradius=0.003)
    vod.drawFarCircle()
    vod.textScale = 0.02
    vod.vertexRadius = 0.0031
    vod.drawVertices=0
    vod.drawVertexIndex=0
    vod.drawGenerators=0
    vod.offsetEdges = 0
    vd.setEdgeOffset(0.05) # for visualization only. NOT offsetting!

    # segments from ttt
    segs = ttt_segments(  "LinuxCNC", 40000)
    segs = translate(segs, -0.06, 0.05)
    segs = modify_segments(segs)
    
	# build a VD from the input geometry
    times = insert_many_polygons(vd,segs)
    print "all sites inserted. "
    print "VD check: ", vd.check() # sanity check
    
    # this filters the diagram so we are left with only the interior or the exterior
    # of the polygon
    # try True/False here and see what happens
    pi = ovd.PolygonInterior( False )
    vd.filter_graph(pi)
    
    # the Offset class outputs 2D offsets given a VD
    of = ovd.Offset( vd.getGraph() ) # pass the created graph to the Offset class
    ofs_list=[]
    t_before = time.time()
    for t in [0.002*x for x in range(1,20)]:
        ofs = of.offset(t) # produce offsets at distance t
        ofs_list.append(ofs)
    t_after = time.time()
    oftime = t_after-t_before
    
    # offset output format
    # ofs will be a list of offset-loops.
    # [loop1, loop2, loop3, ...]
    # each offset-loop contains offset-elements
    # loop1 = [ofs1, ofs2, ofs3, ...]
    # offset elements can be either lines or arcs
    # an offset element is a list:
    # ofs1 = [p, r, cen, cw]
    #  p = the end-point of the offset-element
    #  r = the radius if it is an arc, -1 for lines
    # cen= the center-point if it is an arc
    #  cw= clockwise/anticlockwise flag for arcs
    
    
    # now we draw the offsets in VTK
    print len(ofs_list)," offsets to draw:"
    m=0
    for ofs in ofs_list:
        print m," / ",len(ofs_list)
        offset2vtk.drawOffsets2(myscreen, ofs)
        m=m+1

	# some text on how long Offset ran
    oftext  = ovdvtk.Text()
    oftext.SetPos( (50, 100) )
    oftext_text = "Offset in {0:.3f} s CPU time.".format( oftime )
    oftext.SetText( oftext_text )
    myscreen.addActor(oftext)

    # turn off the whole VD so we can more clearly see the offsets
    # a VD filtered with both True and False is essentially invisible (both the interior and exterior of a polygon removed)
    pi = ovd.PolygonInterior(  True )
    vd.filter_graph(pi)

	# display timing-info on how long the VD build took
    vod.setVDText2(times)
    vod.setAll()
    print "PYTHON All DONE."
    myscreen.render()   
    myscreen.iren.Start()
