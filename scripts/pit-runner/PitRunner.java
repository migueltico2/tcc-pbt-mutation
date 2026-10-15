import org.pitest.mutationtest.config.PluginServices;
import org.pitest.mutationtest.config.ReportOptions;
import org.pitest.mutationtest.tooling.AnalysisResult;
import org.pitest.mutationtest.tooling.EntryPoint;
import org.pitest.util.Glob;

import java.io.File;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;

/**
 * Executa o PIT programaticamente (equivalente ao goal mutationCoverage do pitest-maven),
 * usado apenas no ambiente sem acesso ao Maven Central.
 *
 * Uso: java PitRunner <classpath-do-projeto> <targetClasses> <targetTests> <reportDir> <sourceDir>
 */
public class PitRunner {

    public static void main(String[] args) {
        ReportOptions o = new ReportOptions();
        o.setClassPathElements(Arrays.asList(args[0].split(File.pathSeparator)));
        o.setTargetClasses(List.of(args[1]));
        o.setTargetTests(List.of(new Glob(args[2])));
        o.setReportDir(args[3]);
        o.setSourceDirs(List.of(Path.of(args[4])));
        o.setMutators(List.of("DEFAULTS"));
        o.addOutputFormats(List.of("XML", "CSV"));
        o.setFullMutationMatrix(true);
        o.setShouldCreateTimestampedReports(false);
        o.setNumberOfThreads(Integer.parseInt(System.getProperty("pit.threads", "2")));
        o.setTimeoutConstant(4000);
        o.setVerbosity(org.pitest.util.Verbosity.QUIET_WITH_PROGRESS);
        o.setGroupConfig(new org.pitest.testapi.TestGroupConfig());
        AnalysisResult r = new EntryPoint().execute(new File("."), o, PluginServices.makeForContextLoader(), new HashMap<>());
        if (r.getError().isPresent()) {
            r.getError().get().printStackTrace();
            System.exit(1);
        }
    }
}
