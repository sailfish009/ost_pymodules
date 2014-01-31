"""
Module written by Niklaus Johner (niklaus.johner@a3.epfl.ch) 01.2013
This module is used to align trajectories on a density. It was designed 
for complex lipidic phases such as the lipid cubic phase. It maximizes the overlap
of a selection of atoms with a reference density while minimizing the overlap
of a second selection with that same density. Typically the reference density is water.
"""
try:
  import time
  import math
  import numpy as npy
  import scipy
  from scipy import optimize
  import density_alg,file_utilities
except: 
  print 'module needs time, math, numpy, scipy and scipy.optimize and density_alg modules but could not import them'
  
import os  
from ost import *

__all__=('TransformViewWithPeriodicBoundaries','CalculateDensityOverlapScore',\
        'FindWithinBox','AlignTrajectoryOnDensity','AlignTrajectoryOnFirstFrame')

def _sign(x):
  if x>=0.0:return 1.
  else: return -1.
  
def TransformViewWithPeriodicBoundaries(view,x,cell_center=None,ucell_size=None,ucell_angles=None,group_res=False):
  """
  WARNING: the translational part of x is multiplied by 10 before applying it so it's in [nm]!!
  To make it more stable, we translate the system to the origin, then do the rotation
  translate back and then add the current translation
  PBC are applied before the rotation is made.
  """
  eh=view.handle
  edi=eh.EditXCS()
  ID=geom.Mat4()
  edi.SetTransform(ID)
  TT=geom.Mat4()
  TT.PasteTranslation(10*geom.Vec3(x[0],x[1],x[2]))
  R=geom.Rotation3(x[3],x[4],x[5])
  TR=geom.Mat4()
  TR.PasteRotation(R.GetRotationMatrix())
  #We center the residues in the cell before the transformation
  edi.SetTransform(TT)
  if (cell_center and ucell_size and ucell_angles):
    mol.alg.WrapEntityInPeriodicCell(eh,cell_center,ucell_size,ucell_angles,group_res=group_res)
  edi.SetTransform(ID)
  TCM=geom.Mat4()
  TCM.PasteTranslation(-view.GetCenterOfAtoms())
  TCM2=geom.Mat4()
  TCM2.PasteTranslation(view.GetCenterOfAtoms())
  edi.SetTransform(TT*TCM2*TR*TCM)
  return

def CalculateDensityOverlapScore(x,den_map,view1,view2=None,box_center=None,ucell_size=None,ucell_angles=None):
  t1=time.time()
  TransformViewWithPeriodicBoundaries(view1,x,box_center,ucell_size,ucell_angles)
  vl=mol.alg.GetPosListFromView(view1)
  if not view2:
    return -mol.alg.CalculateAverageAgreementWithDensityMap(vl,den_map)
  else:
    do=mol.alg.CalculateAverageAgreementWithDensityMap(vl,den_map)
    vl2=mol.alg.GetPosListFromView(view2)
    do2=mol.alg.CalculateAverageAgreementWithDensityMap(vl2,den_map)
    return do2-do

def PrintX(x):
  print 'current solution:',x,time.time()

def FindWithinBox(eh,xmin,xmax):
  sele='x>'+str(xmin[0])+' and y>'+str(xmin[1])+' and z>'+str(xmin[2])
  sele+=' and x<'+str(xmax[0])+' and y<'+str(xmax[1])+' and z<'+str(xmax[2])
  return eh.Select(sele)
  
def _TestPBC(t,PBC,cell_center):
  #Verify that we have all we need for the periodic boundary conditions
  if (PBC and not cell_center):
    print 'You have to provide a cell center around which all the frames will get wrapped'
    return False
  if (PBC):
    if any(t.GetFrame(i).GetCellSize()==geom.Vec3() for i in range(t.GetFrameCount())):
      print 'cell size is 0 for some frames'
      return False
    if any(t.GetFrame(i).GetCellAngles()==geom.Vec3() for i in range(t.GetFrameCount())):
      print 'cell angles are 0 for some frames'
      return False
  return True
  
def AlignTrajectoryOnDensity(t,density_map,water_sele,not_water_sele=None,initial_translation=None,PBC=True,cell_center=None,skip_first=True):
  """
  This function Aligns a trajectory on a density.
  It was designed to align trajectories of complex lipidic phases such as the lipid cubic phase.
  It maximizes the overlap of a selection of atoms (water_sele) with the density (density_map)
  while minimizing the overlap of a second selection (not_water_sele) with that same density. 
  Typically the reference density is water.
  t : trajectory
  density_map      : The density used to align the trajectory
  water_sele       : Selection string for the EntityView whose overlap with the density is maximized. If not set, density_sele is used. 
  not_water_sele   : Selection string for the EntityView whose overap with the density is minimized.
  initial_translation : Translation applied before generating the density
  PBC=True         : Use of periodic boundary conditions on the entity during alignment
  cell_center      : center of the cell for wrapping the entity during alignment
  skip_first       : Only apply initial_translation to the first frame, no optimization
  """
  if not _TestPBC(t,PBC,cell_center):return None
  eh=t.GetEntity()
  print 'number of frames to align',t.GetFrameCount()
  xmin_list=[]
  x=scipy.zeros(6)
  if initial_translation:
    for i in range(3):x[i]=initial_translation[i]/10.
  t0=time.time()
  if not PBC:
    ucell_size=None
    ucell_angles=None
  for i in range(t.GetFrameCount()):
    t1=time.time()
    t.CopyFrame(i)
    f=t.GetFrame(i)
    if PBC:
      ucell_size=f.GetCellSize()
      ucell_angles=f.GetCellAngles()
    not_waters=eh.Select(not_water_sele)
    waters=eh.Select(water_sele)
    print 'frame',i,'out of',t.GetFrameCount(),'number of W',waters.GetAtomCount(),'number of not W',not_waters.GetAtomCount()
    if not(skip_first and i==0):
      xmin=optimize.fmin_powell(CalculateDensityOverlapScore,x,args=(density_map,waters,not_waters,cell_center,ucell_size,ucell_angles),maxiter=20,full_output=True,maxfun=2000,disp=False,callback=None)
      x=xmin[0]
      xmin_list.append(xmin)
    print 'frame',i,'finale solution',x,'time for convergence',int(time.time()-t1),'seconds'
    TransformViewWithPeriodicBoundaries(waters,x,cell_center,ucell_size,ucell_angles)
    t.Capture(i)
    eh.SetTransform(geom.Transform())
  print 'total time',int(time.time()-t0),'seconds'
  return xmin_list

def AlignTrajectoryOnFirstFrame(t,density_sele,water_sele=None,not_water_sele=None,initial_translation=None,PBC=True\
                                ,cell_center=None,outdir=None,filename_base='',density_margin=0,density_cutback=False,\
                                density_sampling=1,low_pass_filter_level=10,io_profile=None):
  """
  This function Aligns a trajectory on the density generated from its first frame
  It was designed to align trajectories of complex lipidic phases such as the lipid cubic phase.
  It maximizes the overlap of a selection of atoms (water_sele) with the density of a selection 
  (density_sele), genreated from the first frame, while minimizing the overlap
  of a second selection (not_water_sele) with that same density. Typically the reference density is water.
  t : trajectory
  density_sele     : Selection string used to select the atoms for the generation of the density
  water_sele       : Selection string for the EntityView whose overlap with the density is maximized. If not set, density_sele is used. 
  not_water_sele   : Selection string for the EntityView whose overap with the density is minimized.
  initial_translation : Translation applied before generating the density
  PBC=True         : Use of periodic boundary conditions on the entity during alignment
  cell_center      : center of the cell for wrapping the entity during alignment
  outdir           : path to the output directory for saving files (densities, aligned trajectory)
  filename_base    : base name used for all the files being saved
  density_margin   : size by which the Entity gets extended (using PBCs) before generating the density
  density_cutback  : If True, the density is cutback after generation to its initial size (previous to the extension by density_margin)
  density_sampling : The sampling in real space for the density (# of points per Angstrom).
  low_pass_filter_level : The density gets filtered after generation by a low pass filter with this level in A.
  io_profile       : Profile used to save PDB and dcd files.
  """
  eh=t.GetEntity()
  t.CopyFrame(0)
  if not cell_center:cell_center=eh.GetCenterOfAtoms()
  if not _TestPBC(t,PBC,cell_center):return None
  if not io_profile:io_profile=io.IOProfile(dialect='CHARMM',fault_tolerant=True)
  if not water_sele:water_sele=density_sele
  if PBC:
    ucell_size=t.GetFrame(0).GetCellSize()
    ucell_angles=t.GetFrame(0).GetCellAngles()
    mol.alg.WrapEntityInPeriodicCell(eh,cell_center,ucell_size,ucell_angles,False)
  if initial_translation:
    T=geom.Transform()
    T.SetTrans(initial_translation)
    eh.SetTransform(T)
    cell_center=cell_center+initial_translation
  if outdir:io.SavePDB(eh,os.path.join(outdir,filename_base+'first_frame_centered_wrapped.pdb'),profile=io_profile)
  density_view=eh.Select(density_sele)
  ucell_vecs=t.GetFrame(0).GetCellVectors()
  den_map=density_alg.CreateDensityMapFromEntityView(density_view,density_sampling,5,density_margin,cell_center,ucell_vecs,density_cutback)
  den_map_filtered=den_map.Apply(img.alg.LowPassFilter(low_pass_filter_level))
  eh.SetTransform(geom.Transform())
  if outdir:
    io.SaveMap(den_map_filtered,os.path.join(outdir,filename_base+'density_first_frame_filtered.mrc'))
    io.SaveMap(den_map,os.path.join(outdir,filename_base+'density_first_frame.mrc'))
  x=AlignTrajectoryOnDensity(t,den_map_filtered,water_sele,not_water_sele,initial_translation,PBC,cell_center,skip_first=True)  
  if outdir:
    t.CopyFrame(0)
    io.SaveCHARMMTraj(t,os.path.join(outdir,filename_base+'aligned_trajectory.pdb'),\
    os.path.join(outdir,filename_base+'aligned_trajectory.dcd'),profile=io_profile)
    xmin=[npy.array([initial_translation[0]/10.,initial_translation[1]/10.,initial_translation[2]/10.,0.0,0.0,0.0])]
    xmin.extend([xi[0] for xi in x])
    file_utilities.WriteListOfListsInLines(['x1','x2','x3','r1','r2','r3'],xmin,os.path.join(outdir,filename_base+'aligned_trajectory_transformations.txt'))
  return xmin
  
  