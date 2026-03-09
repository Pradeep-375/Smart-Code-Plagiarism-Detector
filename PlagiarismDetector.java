import java.nio.file.Files;
import java.nio.file.Paths;
public class PlagiarismDetector {
    public static String readFile(String path) throws Exception {
        return new String(Files.readAllBytes(Paths.get(path)));
    }
    public static String preprocess(String s) {
        s = s.replaceAll("//.*", "");
        s = s.replaceAll("\\s+", "");
        return s;
    }
    public static int lcs(String a, String b) {
        int m = a.length();
        int n = b.length();
        int[][] dp = new int[m+1][n+1];
        for(int i=1;i<=m;i++){
            for(int j=1;j<=n;j++){
                if(a.charAt(i-1)==b.charAt(j-1)){
                    dp[i][j]=dp[i-1][j-1]+1;
                }else{
                    dp[i][j]=Math.max(dp[i-1][j],dp[i][j-1]);
                }
            }
        }
        return dp[m][n];
    }
    public static void main(String[] args) throws Exception {
        String file1 = readFile("C:\\Users\\prade\\OneDrive\\Pradeep\\python language\\basicOperation.py");
        String file2 = readFile("C:\\Users\\prade\\OneDrive\\Pradeep\\python language\\factorial.py");
        file1 = preprocess(file1);
        file2 = preprocess(file2);
        int match = lcs(file1,file2);
        double similarity = (2.0*match)/(file1.length()+file2.length())*100;
        System.out.println("Length of File1 : "+file1.length());
        System.out.println("Length of File2 : "+file2.length());
        System.out.println("Matching characters : "+match);
        System.out.println("Similarity : "+similarity+" %");
        if(similarity>60){
            System.out.println("Possible plagiarism detected");
        }else{
            System.out.println("Files are mostly different");
        }
    }
}