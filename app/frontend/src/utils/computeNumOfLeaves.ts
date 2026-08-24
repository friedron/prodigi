export const computeNumOfLeaves = (surrogatePage: any, variablePage: any) => {
  const maxDepth = surrogatePage.modelConfig.gbtConfig.trainConfig.maxDepth;
  if (maxDepth) {
    return Math.pow(2, maxDepth);
  }
  return 0;
};
