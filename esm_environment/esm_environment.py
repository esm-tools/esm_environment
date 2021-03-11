#!/usr/bin/env python
"""
Main module for EsmEnvironment.
"""

import copy
import os
import warnings

import esm_parser
from esm_rcfile import FUNCTION_PATH

######################################################################################
########################### class "environment_infos" ################################
######################################################################################


class EnvironmentInfos:
    def __init__(self, run_or_compile, complete_config=None, model=None):
        # Ensure local copy of complete config to avoid mutating it... (facepalm)
        complete_config = copy.deepcopy(complete_config)
        # Load computer dictionary or initialize it from the correct machine file
        if complete_config and "computer" in complete_config:
            self.config = complete_config["computer"]
        else:
            self.machine_file = esm_parser.determine_computer_from_hostname()
            self.config = esm_parser.yaml_file_to_dict(self.machine_file)
            esm_parser.basic_choose_blocks(self.config, self.config)
            esm_parser.recursive_run_function(
                [],
                self.config,
                "atomic",
                esm_parser.find_variable,
                self.config,
                [],
                True,
            )

        # Add_s can only be inside choose_ blocks in the machine file
        for entry in ["add_module_actions", "add_export_vars"]:
            if entry in self.config:
                del self.config[entry]

        if "general" in complete_config:
            ## Complete information in the general section with ``further_reading``
            #general = copy.deepcopy(complete_config.get("general"), {})
            #esm_parser.attach_to_config_and_remove(general, "further_reading")
            ## Merge the completed information with priority on the already existing
            ## variables in ``complete_config``
            #complete_config["general"] = esm_parser.priority_merge_dicts(
            #    complete_config["general"], general, priority = "first"
            #)
            #if "further_reading" in complete_config["general"]:
            #    del complete_config["general"]["further_reading"]
            #del general

            # Is it a coupled setup?
            coupled_setup = complete_config["general"].get("coupled_setup", False)

            # Check if a general setup environment exists that will overwrite the
            # component setups
            if coupled_setup and (
                "compiletime_environment_changes" in complete_config["general"] or
                "runtime_environment_changes" in complete_config["general"] or
                "environment_changes" in complete_config["general"]
            ):  # TODO: do this if the model include other models and the environment is
                # labelled as priority over the other models environment (OIFS case)
                general_env = True
                self.apply_config_changes(run_or_compile, complete_config, "general")
            else:
                general_env = False

        # If there is a general environment remove all the model specific environments
        # define in the model files and preserve only the model specific environments
        # that are explicitly defined in the setup file
        if general_env:
            self.load_component_env_changes_only_in_setup(complete_config)

        # If the model is defined during the instantiation of the class (e.g.
        # during esm_master with a coupled setup), get the environment for that
        # model. Otherwise, loop through all the keys of the complete_config dictionary
        if model:
            self.apply_config_changes(run_or_compile, complete_config, model)
        else:
            for model in complete_config:
                self.apply_config_changes(run_or_compile, complete_config, model)

        self.add_esm_var()
        self.commands = self.get_shell_commands()

    def add_esm_var(self):
        """Adds the ENVIRONMENT_SET_BY_ESMTOOLS=TRUE to the config, for later
        dumping to the shell script."""
        if "export_vars" in self.config:
            self.config["export_vars"]["ENVIRONMENT_SET_BY_ESMTOOLS"] = "TRUE"
        else:
            self.config["export_vars"] = {"ENVIRONMENT_SET_BY_ESMTOOLS": "TRUE"}

    def apply_config_changes(self, run_or_compile, config, model):
        self.apply_model_changes(
            model, run_or_compile=run_or_compile, modelconfig=config[model]
            )

    def apply_model_changes(self, model, run_or_compile="runtime", modelconfig=None):
        if not modelconfig:
            print("Should not happen anymore...")
            modelconfig = esm_parser.yaml_file_to_dict(
                FUNCTION_PATH + "/" + model + "/" + model
            )
        thesechanges = run_or_compile + "_environment_changes"
        if thesechanges in modelconfig:

# kh 16.09.20 the machine name is already handled here
# additionally handle different versions of the model (i.e. choose_version...) for each machine
# if this is possible here in a more generic way, it can be refactored
            if "choose_version" in modelconfig[thesechanges]:
                if "version" in modelconfig:
                    if modelconfig["version"] in modelconfig[thesechanges]["choose_version"]:
                        for k, v in modelconfig[thesechanges]["choose_version"][modelconfig["version"]].items():

# kh 16.09.20 move up one level and replace default
                            modelconfig[thesechanges][k] = v

                del modelconfig[thesechanges]["choose_version"]

            if "environment_changes" in modelconfig:
                modelconfig["environment_changes"].update(modelconfig[thesechanges])
            else:
                modelconfig["environment_changes"] = modelconfig[thesechanges]

        if "environment_changes" in modelconfig:
            for entry in ["add_module_actions", "add_export_vars"]:
                if not entry in self.config:
                    if entry is "add_module_actions":
                        self.config[entry] = []
                    elif entry is "add_export_vars":
                        self.config[entry] = {}
#                if entry in modelconfig["environment_changes"]:
#                    if isinstance(modelconfig["environment_changes"][entry], list):
#                        self.config[entry] += modelconfig["environment_changes"][
#                            entry
#                        ]
#                    else:
#                        self.config[entry].update(
#                            modelconfig["environment_changes"][entry]
#                        )
#                    del modelconfig["environment_changes"][entry]
                if entry is "add_export_vars":
                    # Find the entry paths
                    path_sep = ","
                    entry_paths = esm_parser.find_key(
                        modelconfig["environment_changes"],
                        entry,
                        paths2finds = [],
                        sep = path_sep,
                    )
                    for entry_path in entry_paths:
                        path_to_var = entry_path.split(path_sep)
                        if len(path_to_var) > 1:
                            export_dict = esm_parser.find_value_for_nested_key(
                                modelconfig["environment_changes"],
                                path_to_var[-2],
                                path_to_var[:-2],
                            )
                        else:
                            export_dict = modelconfig["environment_changes"]
                        export_vars = export_dict[path_to_var[-1]]

                        # Transforms lists in of export_vars in dictionaries. This
                        # allows to add lists of export_vars to the machine-defined
                        # export_vars that should always be a dictionary. Note that
                        # lists are always added at the end of the export_vars, if you
                        # want to edit variables of an already existing ditionary
                        # make your export_var be a dictionary.
                        if isinstance(export_vars, list):
                            new_export_vars = {}
                            for var in export_vars:
                                rep = 0
                                while True:
                                    if var + f"[[{rep}]][[list]]" in new_export_vars:
                                        rep += 1
                                    else:
                                        new_export_vars[
                                            var + f"[[{rep}]][[list]]"
                                        ] = var
                                        break
                            export_dict[path_to_var[-1]] = new_export_vars

            self.config.update(modelconfig["environment_changes"])
            all_keys = self.config.keys()
            for key in all_keys:
                if "choose_computer." in key:
                    newkey = key.replace("computer.", "")
                    self.config[newkey] = self.config[key]
                    del self.config[key]

            esm_parser.basic_choose_blocks(self.config, self.config)

            for entry in ["add_module_actions", "add_export_vars"]:
                if entry in self.config:
                    del self.config[entry]


    def load_component_env_changes_only_in_setup(self, complete_config):
        setup = complete_config.get("general", {}).get("model", None)
        version = complete_config.get("general", {}).get("version", None)
        models = complete_config.get("general", {}).get("models", None)
        if not models:
            print(
                "Use the EnvironmentInfos.load_component_env_changes_only_in_setup " +
                "method only if complete_config has a general chapter that includes " +
                "a models list"
            )
            sys.exit(1)

        include_path, needs_load = esm_parser.look_for_file(
            setup,
            setup + "-" + version,
        )
        if not include_path:
            print(f"File for {setup + '-' + version} not found")
            sys.exit(1)
        if needs_load:
            setup_config = esm_parser.yaml_file_to_dict(include_path)
        else:
            print(f"A setup needs to load a file so this line shouldn't be reached")
            sys.exit(1)

        for attachment in esm_parser.CONFIGS_TO_ALWAYS_ATTACH_AND_REMOVE:
            esm_parser.attach_to_config_and_remove(setup_config, attachment)
            for component in list(setup_config):
                esm_parser.attach_to_config_and_remove(
                    setup_config[component],
                    attachment,
                )

        environment_vars = [
            "environment_changes",
            "compiletime_environment_changes",
            "runtime_environment_changes",
        ]
        for model in models:
            if model not in complete_config:
                print(f"The chapter {model} does not exist in complete_config")
                sys.exit(1)
            model_config = complete_config[model]
            for env_var in environment_vars:
                if env_var in model_config:
                    del model_config[env_var]
                if env_var in setup_config.get(model, {}):
                    esm_parser.recursive_run_function(
                        [],
                        setup_config[model][env_var],
                        "atomic",
                        esm_parser.find_variable,
                        complete_config,
                        {},
                        {},
                    )
                    model_config[env_var] = setup_config[model][env_var]


    def replace_model_dir(self, model_dir):
        """
        Replaces any instances of ${model_dir} in the config section
        "export_vars" with the argument

        Parameters
        ----------
        model_dir : str
            The replacement string for ${model_dir}
        """
        for entry in ["export_vars"]:
            if entry in self.config:
                newlist = []
                for line in self.config[entry]:
                    newline = line.replace("${model_dir}", model_dir)
                    newlist.append(newline)
                self.config[entry] = newlist

    def get_shell_commands(self):
        """
        Gathers module actions and export variables from the config to a list,
        prepending appropriate shell command words (e.g. module and export)

        Returns
        -------
        list
        """
        environment = []
        if "module_actions" in self.config:
            for action in self.config["module_actions"]:
				    # seb-wahl: workaround to allow source ... to be added to the batch header
					 # until a proper solution is available. Required with FOCI
                if action.startswith("source"):
                    environment.append(action)
                else:
                    environment.append("module " + action)
        # Add an empty string as a newline:
        environment.append("")
        if "export_vars" in self.config:
            for var in self.config["export_vars"]:
                if isinstance(var, dict):
                    key = list(var.keys())[0]
                    value = var[key]
                    environment.append("export " + key + "='" + str(value) + "'")
                # If the variable is not a dictionary itself but export_vars is
                elif isinstance(self.config["export_vars"], dict):
                    key = var
                    value = self.config["export_vars"][key]
                    # If the variable was added as a list produce the correct string
                    if key.endswith("[[list]]"):
                        key = key.replace("[[list]]", "")
                        environment.append("export " + value)
                    else:
                        environment.append("export " + key + "=" + str(value))
                else:
                    environment.append("export " + str(var))
        return environment

    def write_dummy_script(self, include_set_e=True):
        """
        Writes a dummy script containing only the header information, module
        commands, and export variables. The actual compile/configure commands
        are added later.

        Parameters
        ----------
        include_set_e : bool
            Default to True, whether or not to include a ``set -e`` at the
            beginning of the script. This causes the shell to stop as soon as
            an error is encountered.
        """
        with open("dummy_script.sh", "w") as script_file:
            script_file.write(
                "# Dummy script generated by esm-tools, to be removed later: \n"
            )
            if include_set_e:
                script_file.write("set -e\n")
            for command in self.commands:
                script_file.write(command + "\n")
            script_file.write("\n")

    @staticmethod
    def cleanup_dummy_script():
        """Removes the ``dummy_script.sh`` if it exists."""
        try:
            os.remove("dummy_script.sh")
        except OSError:
            print("No file dummy_script.sh there; nothing to do...")

    @staticmethod
    def add_commands(commands, name):
        """
        Writes all commands in a list to a file named ``<name>_script.sh``,
        located in the current working directory. The header from this script
        is read from ``dummy_script.sh``, also in the current working
        directory.

        Parameters
        ----------
        commands : list of str
            List of the commands to write to the file after the header
        name : str
            Name of the script, generally something like ``comp_echam-6.3.05``

        Returns
        -------
        str :
            ``name`` + "_script.sh"
        """
        if commands:
            with open(name + "_script.sh", "w") as newfile:
                with open("dummy_script.sh", "r") as dummy_file:
                    newfile.write(dummy_file.read())
                for command in commands:
                    newfile.write(command + "\n")
        return name + "_script.sh"

    def output(self):
        esm_parser.pprint_config(self.config)


class environment_infos(EnvironmentInfos):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Please change your code to use EnvironmentInfos!",
            DeprecationWarning,
            stacklevel=2,
        )
        super(environment_infos, self).__init__(*args, **kwargs)
